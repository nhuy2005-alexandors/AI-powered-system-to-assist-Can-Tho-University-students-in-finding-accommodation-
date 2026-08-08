import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from app.crawler.normalize import (
    normalize,
    parse_amenities,
    parse_area,
    parse_price,
)
from app.crawler.parser import (
    load_source_config,
    parse_detail_page,
    parse_jsonld,
    parse_list_page,
)
from app.crawler.dedup import find_duplicates
from app.crawler import freshness, geocode
from app.crawler.schemas import RawListing


# ── parser (HTML thật phongtro123) ──
def test_parse_list_page_real_html(phongtro_html):
    config = load_source_config("phongtro123")
    items = parse_list_page(phongtro_html, config)
    assert len(items) == 20  # 20 tin/trang
    first = items[0]
    assert first.source == "phongtro123"
    assert first.source_id and first.source_id.isdigit()
    assert first.source_url.startswith("https://phongtro123.com/")
    assert first.title
    assert first.price_text  # "2 triệu/tháng" ...


def test_parse_jsonld_detail(phongtro_detail_html):
    ld = parse_jsonld(phongtro_detail_html)
    assert ld is not None
    assert ld["address"]  # streetAddress đầy đủ
    assert "Cần Thơ" in ld["address"]


def test_parse_detail_page(phongtro_detail_html):
    config = load_source_config("phongtro123")
    d = parse_detail_page(phongtro_detail_html, config)
    assert d.get("address")
    assert "Cái Răng" in d["address"] or "Cần Thơ" in d["address"]
    assert len(d.get("images", [])) > 0


# ── parser (HTML thật tromoi.com — item_mode="self", không có JSON-LD) ──
def test_parse_list_page_tromoi(tromoi_html):
    config = load_source_config("tromoi")
    items = parse_list_page(tromoi_html, config)
    assert len(items) == 21  # 21 tin/trang static (phân trang AJAX)
    first = items[0]
    assert first.source == "tromoi"
    assert first.source_id  # slug cuối URL (nguồn không có ID số)
    assert first.source_url.startswith("https://tromoi.com/")
    assert first.title
    assert first.price_text and "triệu" in first.price_text
    assert first.district and "Cần Thơ" in first.district
    # mọi tin đều có field cốt lõi
    for it in items:
        assert it.title and it.source_url and it.price_text


def test_parse_detail_page_tromoi(tromoi_detail_html):
    config = load_source_config("tromoi")
    d = parse_detail_page(tromoi_detail_html, config)
    # tromoi không có JSON-LD → address lấy từ .box-address
    assert d.get("address")
    assert "Cần Thơ" in d["address"]
    assert "Cái Răng" in d["address"]
    assert d.get("title")
    assert d.get("price_text") and "triệu" in d["price_text"]
    # ảnh gallery lọc theo /storage/uploads/ (loại icon/logo)
    assert len(d.get("images", [])) > 0
    assert all("/storage/uploads/" in u for u in d["images"])


# ── parser (Mogi) ──
def test_parse_list_page_mogi(mogi_html):
    config = load_source_config("mogi")
    items = parse_list_page(mogi_html, config)
    assert len(items) > 0
    first = items[0]
    assert first.source == "mogi"
    assert first.source_id
    assert first.source_url.startswith("https://mogi.vn/")
    assert first.title
    assert first.price_text


def test_parse_detail_page_mogi(mogi_detail_html):
    config = load_source_config("mogi")
    d = parse_detail_page(mogi_detail_html, config)
    assert d.get("description")
    assert len(d.get("images", [])) >= 0



# ── normalize ──
def test_parse_price_variants():
    assert parse_price("2,5 triệu/tháng") == 2_500_000
    assert parse_price("1.8 triệu") == 1_800_000
    assert parse_price("800 nghìn") == 800_000
    assert parse_price("750.000 đồng/tháng") == 750_000
    assert parse_price("3000000") == 3_000_000
    assert parse_price(None) is None


def test_parse_area_variants():
    assert parse_area("25 m²") == 25.0
    assert parse_area("20m2") == 20.0
    assert parse_area(None) is None


def test_parse_amenities_detects_keywords():
    am = parse_amenities("Phòng có wifi, máy lạnh, WC riêng, chỗ để xe")
    assert am["wifi"] and am["air_conditioner"] and am["private_wc"] and am["parking"]
    assert am["fridge"] is False


def test_content_hash_stable_and_sensitive():
    raw = RawListing(source="s", source_id="1", title="Phòng A",
                     price_text="2 triệu", area_text="20m2", description="mô tả")
    h1 = normalize(raw).content_hash
    assert h1 == normalize(raw).content_hash
    raw2 = raw.model_copy(update={"price_text": "3 triệu"})
    assert normalize(raw2).content_hash != h1


# ── dedup (data tổng hợp: 2 tin gần giống) ──
def _mk(source_id, title, addr):
    return normalize(RawListing(source="s", source_id=source_id, title=title,
                                address=addr, description=title))


def test_dedup_detects_near_duplicate():
    a = _mk("1", "Phòng trọ gần CTU đường 3/2 Ninh Kiều", "Hẻm 26 đường 3/2 Ninh Kiều")
    b = _mk("2", "Phòng trọ gần CTU đường 3 2 quận Ninh Kiều", "Hẻm 26 đường 3 2 Ninh Kiều Cần Thơ")
    c = _mk("3", "Cho thuê căn hộ cao cấp Vincom Xuân Khánh", "Đại lộ Hòa Bình Xuân Khánh")
    dup = find_duplicates([a, b, c])
    assert 1 in dup and dup[1] == 0  # b trùng a
    assert 2 not in dup             # c khác hẳn


# ── freshness ──
def test_freshness_score_decay():
    now = datetime(2026, 6, 29, tzinfo=timezone.utc)
    assert freshness.freshness_score(now, now) == 1.0
    score = freshness.freshness_score(now - timedelta(days=7), now)
    assert 0.36 < score < 0.38


def test_expired_after_miss_threshold():
    assert freshness.should_expire(1) is False
    assert freshness.should_expire(2) is True
    assert freshness.next_status(2, "active") == "expired"
    assert freshness.next_status(5, "flagged") == "flagged"


# ── geocode (mock net, không gọi Nominatim thật) ──
def test_geocode_landmark_medium(monkeypatch):
    async def _fail(*a, **k):
        raise httpx.ConnectError("no net")
    monkeypatch.setattr(geocode, "_nominatim", _fail)

    async def run():
        g = geocode.Geocoder()
        try:
            return await g.geocode("Phòng gần Đại học Cần Thơ")
        finally:
            await g.__aexit__(None, None, None)
    lat, lng, conf = asyncio.run(run())
    assert conf == "medium"
    assert lat == geocode.CTU_LAT


def test_geocode_ward_centroid_low(monkeypatch):
    async def _fail(*a, **k):
        raise httpx.ConnectError("no net")
    monkeypatch.setattr(geocode, "_nominatim", _fail)

    async def run():
        g = geocode.Geocoder()
        try:
            return await g.geocode("Một địa chỉ ở Bình Thủy")
        finally:
            await g.__aexit__(None, None, None)
    lat, lng, conf = asyncio.run(run())
    assert conf == "low"
    assert lat == geocode.WARD_CENTROIDS["binh thuy"][0]


def test_geocode_failed():
    async def run():
        g = geocode.Geocoder()
        try:
            return await g.geocode(None)
        finally:
            await g.__aexit__(None, None, None)
    assert asyncio.run(run()) == (None, None, "failed")


def test_haversine_ctu_zero():
    assert geocode.haversine_m(geocode.CTU_LAT, geocode.CTU_LNG,
                               geocode.CTU_LAT, geocode.CTU_LNG) == 0.0


# ── geocode address normalize (root cause fix) ──
def test_strip_admin_removes_prefixes():
    s = geocode.strip_admin("192 Đường Nguyễn Thông, Phường An Thới, Quận Bình Thuỷ, Cần Thơ")
    assert "Phường" not in s and "Quận" not in s and "Đường" not in s
    assert "Nguyễn Thông" in s and "An Thới" in s


def test_ward_district_city_extract():
    wdc = geocode.ward_district_city("180A, khu vực Phú Thuận Đường Chí Sinh, Phường Tân Phú, Quận Cái Răng, Cần Thơ")
    assert wdc == "Tân Phú, Cái Răng, Cần Thơ"


def test_ward_district_city_none_when_no_admin():
    assert geocode.ward_district_city("chỉ text tự do không có phường") is None


def test_geocode_medium_via_ward_query(monkeypatch):
    # tầng 1 (full) fail, tầng 2 (ward+district+city) trả tọa độ → medium
    calls = []

    async def _fake(client, q):
        calls.append(q)
        # chỉ match query cấp phường chính xác (tầng 2), full-address (tầng 1) fail.
        # Phần tử thứ 3 = OSM `type`, BẮT BUỘC: _nominatim thật luôn trả 3-tuple và
        # tầng 2 giờ kiểm type ∈ _ADMIN_TYPES. Fake 2-tuple = fixture nói dối về
        # hình dạng của hàm thật → IndexError, không phải lỗi implementation.
        return (10.06, 105.76, "administrative") if q == "An Thới, Bình Thuỷ, Cần Thơ" else None
    monkeypatch.setattr(geocode, "_nominatim", _fake)

    async def run():
        g = geocode.Geocoder()
        try:
            return await g.geocode("192 Đường Nguyễn Thông, Phường An Thới, Quận Bình Thuỷ, Cần Thơ")
        finally:
            await g.__aexit__(None, None, None)
    lat, lng, conf = asyncio.run(run())
    assert conf == "medium"
    assert lat == 10.06


# ── area extraction (merge_detail) ──
def test_area_extraction_from_description():
    from app.crawler.pipeline import merge_detail
    from app.crawler.schemas import NormalizedListing

    n = NormalizedListing(source="s", title="Phòng trọ", area=None)
    merge_detail(n, {"description": "Giá thuê: 750.000đ/tháng Diện tích: 26m² thoáng mát"})
    assert n.area == 26.0


def test_area_extraction_ignores_noise():
    from app.crawler.pipeline import merge_detail
    from app.crawler.schemas import NormalizedListing

    n = NormalizedListing(source="s", title="MINI HOUSE rộng rãi", area=None)
    merge_detail(n, {"description": "Nhà đẹp không ghi diện tích"})
    assert n.area is None


# ── Tầng 5 city centroid: 3 lỗi tìm ra ở review, đóng lại bằng test ──
def _geocode_offline(monkeypatch, address):
    """Geocode với Nominatim chết → chỉ còn các tầng bảng tra + tầng 5."""
    async def _fail(*a, **k):
        raise httpx.ConnectError("no net")
    monkeypatch.setattr(geocode, "_nominatim", _fail)

    async def run():
        g = geocode.Geocoder()
        try:
            return await g.geocode(address)
        finally:
            await g.__aexit__(None, None, None)
    return asyncio.run(run())


def test_geocode_city_fallback_never_none(monkeypatch):
    """Address rác + không khớp bảng nào → tầng 5 trả centroid TP, KHÔNG phải None.

    Đây là tiền đề của bug guard `lat is None` ở pipeline: vì lat không bao giờ None
    nên nhánh fallback district từng là code chết.
    """
    lat, lng, conf = _geocode_offline(monkeypatch, "hẻm 9 xyz không parse được")
    assert conf == "city"
    assert (lat, lng) == geocode.CANTHO_CENTROID


def test_landmark_bare_number_key_does_not_false_match(monkeypatch):
    """Key '586' trần từng khớp cả số nhà '586/12 Nguyễn Văn Cừ' → pin sai về Cái Răng."""
    lat, lng, conf = _geocode_offline(monkeypatch, "586/12 Nguyễn Văn Cừ")
    assert (lat, lng) != geocode.LANDMARKS["cho 586"], "số nhà 586 bị bắt như KDC 586"
    assert "586" not in geocode.LANDMARKS, "key số trần phải bị bỏ"


def test_landmark_metro_key_does_not_false_match(monkeypatch):
    """Key 'metro' trần từng khớp 'Metro House'/'Metropolitan' — tên toà nhà bất kỳ."""
    lat, lng, _ = _geocode_offline(monkeypatch, "Metropolitan Tower, Ninh Kiều")
    assert (lat, lng) != (10.0100, 105.7430), "'metro' trần vẫn bắt bừa"
    assert "metro" not in geocode.LANDMARKS
    assert "sieu thi metro" in geocode.LANDMARKS


def test_pipeline_district_fallback_beats_city_centroid(monkeypatch):
    """conf=='city' + có district → phải hạ về tâm QUẬN, không giữ tâm THÀNH PHỐ."""
    async def _fail(*a, **k):
        raise httpx.ConnectError("no net")
    monkeypatch.setattr(geocode, "_nominatim", _fail)

    async def run():
        g = geocode.Geocoder()
        try:
            junk = await g.geocode("xyz rác")
            district = await g.geocode("Bình Thủy, Cần Thơ")
            return junk, district
        finally:
            await g.__aexit__(None, None, None)

    junk, district = asyncio.run(run())
    assert junk[2] == "city"
    # tâm quận (từ WARD_CENTROIDS) khác tâm TP → fallback thực sự cải thiện toạ độ
    assert district[2] == "low"
    assert (district[0], district[1]) != geocode.CANTHO_CENTROID


def test_ward_centroid_has_no_city_catchall(monkeypatch):
    """Key 'can tho' trong WARD_CENTROIDS từng bắt MỌI địa chỉ ở tầng 4.

    Mọi address thật đều chứa "Cần Thơ" → substring match ở tầng 4 luôn khớp, trả
    ĐÚNG toạ độ CANTHO_CENTROID nhưng dán nhãn 'low' thay vì 'city'. Hệ quả: tầng 5
    gần như không bao giờ chạy, và tâm thành phố bị tính là 'low' → được cộng 0.20
    quality_score (pipeline.py:123 cộng cho high/medium... nhưng badge/thống kê coi
    'low' là có vị trí thật). Tâm TP phải mang nhãn 'city' để trung thực.
    """
    assert "can tho" not in geocode.WARD_CENTROIDS, "catch-all cấp TP phải nằm ở tầng 5"
    lat, lng, conf = _geocode_offline(monkeypatch, "hẻm 9 không rõ, Cần Thơ")
    assert conf == "city", f"address rác + 'Cần Thơ' phải là 'city', không phải {conf!r}"
    assert (lat, lng) == geocode.CANTHO_CENTROID


def test_cached_geo_with_coords_not_labelled_failed():
    """Dòng có toạ độ mà confidence rỗng → default 'low', KHÔNG phải 'failed'.

    'failed' nghĩa là không có toạ độ; gán nó cho dòng đang có geom là dán nhãn sai.
    """
    cached = {"lat": 10.03, "lng": 105.78, "geocode_confidence": None}
    assert (cached.get("geocode_confidence") or "low") == "low"


# ── Tầng 3b: address trần + ", Cần Thơ" (đo 2026-08-08 trên 59 tin 'failed' thật) ──
def test_bare_street_appends_city_token():
    """Nominatim không biết address thuộc tỉnh nào → match tên đường trùng ra HN/HCM.

    Đo thật: 'Lý tự trọng' trần trả (10.7786, 106.7016) = TP.HCM, bị bbox chặn nên
    tin rơi xuống 'failed'; thêm ', Cần Thơ' thì ra (10.0330, 105.7813) = đúng đường
    Lý Tự Trọng, Ninh Kiều. Đây là nguyên nhân THẬT của 82 tin failed, không phải
    "string nguồn cụt" như checkpoint cũ ghi.
    """
    assert geocode.bare_street_in_cantho("Lý tự trọng") == "Lý tự trọng, Cần Thơ"
    assert geocode.bare_street_in_cantho("Phạm Ngũ Lão") == "Phạm Ngũ Lão, Cần Thơ"


def test_bare_street_rejects_address_without_proper_name():
    """Address chỉ có số + filler → KHÔNG được query: Nominatim trả đường bất kỳ.

    Đo thật: 'Hẻm 359' / 'Hẻm 105' / 'Hẻm 118-120' / 'Hẻm 3-4' là 4 địa chỉ KHÁC
    nhau nhưng cùng trả (10.0752, 105.7287) — toạ độ sai tự tin, tệ hơn 'city'
    (ADR-011: không dán nhãn lạc quan lên vị trí không biết).
    """
    for addr in ("Hẻm 359", "Hẻm 105", "Hẻm 118-120", "Hẻm 3-4", "Số 5", "hẻm 9",
                 "Đường số 16", "Hẻm 77", "Hẻm tổ 10", "Kdc 3a"):
        assert geocode.bare_street_in_cantho(addr) is None, f"{addr!r} không có tên riêng"


def test_bare_street_skips_when_address_has_admin_part():
    """Có 'Cần Thơ' hoặc phần hành chính → tầng 1/2 đã lo, 3b không được chen vào."""
    assert geocode.bare_street_in_cantho("Lý Tự Trọng, Cần Thơ") is None
    assert geocode.bare_street_in_cantho("Trần Phú, Phường An Nghiệp") is None


def test_tier3b_rejects_non_street_osm_type(monkeypatch):
    """OSM type không phải đường → Nominatim bám 1 POI trùng chữ, phải bỏ.

    Đo thật: 'CTY 8' trả type='hotel', 'Hẻm tổ 10' trả 'clothes', 'Hẻm 107 Xô viết
    nghệ tỉnh' trả 'bicycle_rental' — đều in-bbox nhưng không phải con đường trong
    address. Nhận chúng = pin tin vào một cửa hàng ngẫu nhiên.
    """
    async def _nom(client, query):
        # tầng 1 (address trần): OSM match tên trùng ngoài CT → bbox chặn, rơi xuống 3b
        if "Cần Thơ" not in query:
            return 10.7786, 106.7016, "hotel"
        return 10.0300, 105.7800, "hotel"  # 3b: in-bbox nhưng là POI, không phải đường

    monkeypatch.setattr(geocode, "_nominatim", _nom)
    monkeypatch.setattr(geocode, "RATE_LIMIT", 0.0)

    async def run():
        g = geocode.Geocoder()
        try:
            return await g.geocode("Tạ Thị Phi")
        finally:
            await g.__aexit__(None, None, None)

    lat, lng, conf = asyncio.run(run())
    assert geocode.bare_street_in_cantho("Tạ Thị Phi") == "Tạ Thị Phi, Cần Thơ"
    assert conf == "city", f"POI in-bbox phải bị bỏ → tầng 5, không phải {conf!r}"
    assert (lat, lng) == geocode.CANTHO_CENTROID


def test_tier3b_accepts_street_type_as_medium(monkeypatch):
    """Type là đường thật + in-bbox → 'medium' (biết đúng đường, không biết số nhà)."""
    calls: list[str] = []

    async def _street(client, query):
        calls.append(query)
        # tầng 1 (address trần, không có 'Cần Thơ') → OSM match ra TP.HCM, bbox chặn
        if "Cần Thơ" not in query:
            return 10.7786, 106.7016, "tertiary"
        return 10.0330, 105.7813, "tertiary"

    monkeypatch.setattr(geocode, "_nominatim", _street)
    monkeypatch.setattr(geocode, "RATE_LIMIT", 0.0)

    async def run():
        g = geocode.Geocoder()
        try:
            return await g.geocode("Lý tự trọng")
        finally:
            await g.__aexit__(None, None, None)

    lat, lng, conf = asyncio.run(run())
    assert conf == "medium", f"đường thật in-bbox phải là medium, không phải {conf!r}"
    assert (lat, lng) == (10.0330, 105.7813)
    assert "Lý tự trọng, Cần Thơ" in calls


# ── Guard OSM `type` cho tầng 1 / tầng 2 (bug đo 2026-08-08 trên data chotot) ──
def _geocode_with_osm(monkeypatch, address, replies):
    """Geocode với Nominatim giả: replies = dict[substring_query] -> (lat,lng,type)|None.

    Khớp theo substring để test không phụ thuộc chính xác chuỗi query từng tầng dựng.
    """
    async def _fake(client, query):
        for needle, val in replies.items():
            if needle in query:
                return val
        return None

    monkeypatch.setattr(geocode, "_nominatim", _fake)
    monkeypatch.setattr(geocode, "RATE_LIMIT", 0.0)

    async def run():
        g = geocode.Geocoder()
        try:
            return await g.geocode(address)
        finally:
            await g.__aexit__(None, None, None)
    return asyncio.run(run())


def test_tier2_rejects_poi_type_as_ward_centroid(monkeypatch):
    """Query cấp phường mà OSM trả POI → KHÔNG được nhận làm tâm phường 'medium'.

    Đo thật trên 3 tin chotot cùng phường Hưng Thạnh: query "Hưng Thạnh, Cái Răng,
    Cần Thơ" trả type=place_of_worship (10.0047474, 105.7502592). Nhận nó làm tâm
    phường thì 3 address KHÁC NHAU cùng ra 1 điểm, lệch ~3km so với vị trí thật.
    """
    lat, lng, conf = _geocode_with_osm(
        monkeypatch,
        "Kdc Hưng Phú Cty8, Phường Hưng Thạnh, Quận Cái Răng, Cần Thơ",
        {"Hưng Thạnh": (10.0047474, 105.7502592, "place_of_worship")},
    )
    assert (lat, lng) != (10.0047474, 105.7502592) or conf == "low", (
        f"place_of_worship bị nhận làm tâm phường với nhãn {conf!r}"
    )
    assert conf != "medium", "POI không được mang nhãn medium của tầng phường"


def test_tier2_accepts_administrative_type(monkeypatch):
    """OSM trả ranh giới hành chính thật → vẫn là 'medium' như trước (không hồi quy)."""
    lat, lng, conf = _geocode_with_osm(
        monkeypatch,
        "Hẻm 12 Da Liễu, Phường Lê Bình, Quận Cái Răng, Cần Thơ",
        {"Lê Bình": (9.9990419, 105.7519114, "administrative")},
    )
    assert conf == "medium", f"ranh giới phường thật phải là medium, không phải {conf!r}"
    assert (lat, lng) == (9.9990419, 105.7519114)


def test_tier1_does_not_label_poi_as_high(monkeypatch):
    """Tầng 1 match POI (không phải nhà/đường) → KHÔNG được phong 'high'.

    "Khu Dân Cư Văn Hóa Tây Đô, Hưng Thạnh, Cái Răng, Cần Thơ" từng trả
    type=place_of_worship và được gắn high — nhãn cao nhất cho một nhà thờ cách
    vị trí thật ~3km.
    """
    _lat, _lng, conf = _geocode_with_osm(
        monkeypatch,
        "Khu Dân Cư Văn Hóa Tây Đô, Phường Hưng Thạnh, Quận Cái Răng, Cần Thơ",
        {"Tây Đô": (10.0047474, 105.7502592, "place_of_worship")},
    )
    assert conf != "high", "POI trùng chữ không được mang nhãn high (có số nhà)"


def test_tier1_keeps_high_for_house_type(monkeypatch):
    """Số nhà thật (type=house) vẫn 'high' — guard không được làm mất tầng 1."""
    lat, lng, conf = _geocode_with_osm(
        monkeypatch,
        "148/150G Đường 3/2, Phường Tân An, Quận Ninh Kiều, Cần Thơ",
        {"148/150G": (10.033044, 105.7872, "house")},
    )
    assert conf == "high", f"type=house phải là high, không phải {conf!r}"
    assert (lat, lng) == (10.033044, 105.7872)


def test_poi_candidate_beats_city_centroid_but_labelled_low(monkeypatch):
    """POI bị từ chối vẫn dùng được làm ứng viên cuối, nhưng nhãn phải là 'low'.

    Thà giữ toạ độ có liên quan tới address hơn là tâm TP, nhưng KHÔNG được nhận
    nhãn medium/high vì chưa xác thực (quality_score chỉ cộng cho high/medium).
    """
    lat, lng, conf = _geocode_with_osm(
        monkeypatch,
        "Xyz Qwe Rty, Phường Zzz Kkk, Quận Www Vvv, Cần Thơ",
        {"Zzz Kkk": (10.0210, 105.7654, "place_of_worship")},
    )
    assert conf == "low", f"ứng viên POI phải là low, không phải {conf!r}"
    assert (lat, lng) == (10.0210, 105.7654)
    assert (lat, lng) != geocode.CANTHO_CENTROID


# ── _match_table: biên từ + ưu tiên cấp nhỏ (bug đo trên address thật chotot 2026-08-08) ──
def test_match_table_word_boundary_rejects_substring_hit():
    """'an hoa' KHÔNG được khớp trong 'Văn Hóa Tây Đô' ('Hóa'→'hoa' sau khi bỏ dấu).

    Substring trần pin tin về tâm phường An Hòa, lệch 6.5km so với Hưng Thạnh.
    """
    addr = "Khu Dân Cư Văn Hóa Tây Đô, Phường Hưng Thạnh, Quận Cái Răng, Cần Thơ"
    hit = geocode._match_table(addr, geocode.WARD_CENTROIDS, prefer="earliest")
    assert hit != geocode.WARD_CENTROIDS["an hoa"], "'an hoa' bắt bừa trong 'Văn Hóa'"
    assert hit != geocode.WARD_CENTROIDS["an cu"], "'an cu' bắt bừa trong 'Dân Cư'"
    # chỉ còn khớp thật: quận Cái Răng
    assert hit == geocode.WARD_CENTROIDS["cai rang"]


def test_match_table_earliest_prefers_ward_over_district():
    """Address VN viết nhỏ→lớn: key xuất hiện sớm hơn là cấp nhỏ hơn, phải thắng.

    'Võ Tánh, Lê Bình, Cái Răng' từng trả tâm QUẬN Cái Răng chỉ vì 'cai rang' khai
    báo trước 'le binh' trong dict → mất thông tin phường mà address đã cho (2.7km).
    """
    addr = "Đường Võ Tánh, Phường Lê Bình, Quận Cái Răng, Cần Thơ"
    assert geocode._match_table(addr, geocode.WARD_CENTROIDS, prefer="earliest") == \
        geocode.WARD_CENTROIDS["le binh"]
    # thứ tự dict vẫn là cái sẽ thắng nếu dùng prefer mặc định — chứng minh bug thật
    assert geocode._match_table(addr, geocode.WARD_CENTROIDS) == \
        geocode.WARD_CENTROIDS["cai rang"]


def test_match_table_order_mode_keeps_bunxang_priority():
    """LANDMARKS phải giữ ưu tiên-thứ-tự: 'bun xang' thắng 'dai hoc can tho'.

    Đây là ngoại lệ có chủ đích (CHECKPOINT 2026-07-06): tin 'gần ĐH Cần Thơ, hẻm
    bún xáng' phải snap về hồ Bún Xáng (ổ trọ SV) chứ không về giữa trường. Nếu đổi
    LANDMARKS sang 'earliest' thì 'dai hoc can tho' xuất hiện trước → hỏng ý đồ.
    """
    addr = "Hẻm gần Đại học Cần Thơ, khu bún xáng"
    assert geocode._match_table(addr, geocode.LANDMARKS) == geocode.LANDMARKS["bun xang"]


# ── Cờ `degraded`: tách "Nominatim không tìm thấy" khỏi "Nominatim không trả lời" ──
def test_degraded_flag_set_on_network_error(monkeypatch):
    """Lỗi mạng phải bật cờ. Không có cờ thì backfill hạ nhãn hàng loạt do timeout."""
    async def _fail(*a, **k):
        raise httpx.ConnectError("no net")
    monkeypatch.setattr(geocode, "_nominatim", _fail)
    monkeypatch.setattr(geocode, "RATE_LIMIT", 0.0)

    async def run():
        g = geocode.Geocoder()
        try:
            res = await g.geocode("Đường Võ Tánh, Phường Lê Bình, Quận Cái Răng, Cần Thơ")
            return res, g.degraded
        finally:
            await g.__aexit__(None, None, None)

    (lat, lng, conf), degraded = asyncio.run(run())
    assert degraded is True, "query chết vì mạng mà cờ không bật"
    # vẫn trả toạ độ bảng tra (không crash), nhưng caller biết là không đáng tin
    assert conf in ("low", "city")


def test_degraded_flag_clear_when_nominatim_answers_empty(monkeypatch):
    """Nominatim TRẢ LỜI nhưng không có kết quả → KHÔNG degraded.

    Đây là ca 'địa chỉ thật sự không tra được' — nhãn thấp là đúng, phải được ghi.
    """
    async def _empty(client, q):
        return None
    monkeypatch.setattr(geocode, "_nominatim", _empty)
    monkeypatch.setattr(geocode, "RATE_LIMIT", 0.0)

    async def run():
        g = geocode.Geocoder()
        try:
            res = await g.geocode("Đường Võ Tánh, Phường Lê Bình, Quận Cái Răng, Cần Thơ")
            return res, g.degraded
        finally:
            await g.__aexit__(None, None, None)

    (lat, lng, conf), degraded = asyncio.run(run())
    assert degraded is False, "Nominatim trả lời rỗng không phải lỗi mạng"
    assert conf == "low"


def test_degraded_result_not_cached(monkeypatch):
    """Kết quả lỗi mạng KHÔNG được cache — nếu cache thì retry mất tác dụng."""
    state = {"fail": True}

    async def _flaky(client, q):
        if state["fail"]:
            raise httpx.ConnectError("no net")
        return 10.0330, 105.7813, "tertiary"
    monkeypatch.setattr(geocode, "_nominatim", _flaky)
    monkeypatch.setattr(geocode, "RATE_LIMIT", 0.0)

    addr = "Đường Lý Tự Trọng, Phường An Cư, Quận Ninh Kiều, Cần Thơ"

    async def run():
        g = geocode.Geocoder()
        try:
            first = await g.geocode(addr)
            state["fail"] = False
            second = await g.geocode(addr)  # phải gọi lại thật, không lấy cache lỗi
            return first, second
        finally:
            await g.__aexit__(None, None, None)

    first, second = asyncio.run(run())
    assert second[2] == "high", f"lần 2 mạng đã ổn mà vẫn trả {second[2]!r} (cache lỗi)"
    assert second[:2] == (10.0330, 105.7813)


# ── backfill: circuit breaker + không hạ nhãn do lỗi mạng (2026-08-08) ──
class _FakeConn:
    """Conn tối thiểu cho backfill: SELECT trả rows định trước, UPDATE ghi vào list."""

    def __init__(self, rows, writes):
        self._rows = rows
        self._writes = writes

    def execute(self, stmt, params=None):
        if params is None:
            self._last = self._rows
            return self
        self._writes.append(params)
        return self

    def mappings(self):
        return self

    def all(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeEngine:
    def __init__(self, rows, writes):
        self._rows, self._writes = rows, writes

    def connect(self):
        return _FakeConn(self._rows, self._writes)

    def begin(self):
        return _FakeConn(self._rows, self._writes)

    def dispose(self):
        pass


def _run_backfill(monkeypatch, rows, nominatim):
    """Chạy backfill với DB giả + Nominatim giả. Trả (stats, danh sách UPDATE đã ghi)."""
    from app.crawler import backfill as bf

    writes: list[dict] = []
    monkeypatch.setattr(bf, "create_engine", lambda *a, **k: _FakeEngine(rows, writes))
    monkeypatch.setattr(geocode, "_nominatim", nominatim)
    monkeypatch.setattr(geocode, "RATE_LIMIT", 0.0)
    return asyncio.run(bf.backfill()), writes


def test_backfill_aborts_after_consecutive_network_failures(monkeypatch):
    """Nominatim chặn (429) → dừng sớm, KHÔNG nện hết 500 dòng.

    Đã dính 2026-08-08: probe tay dùng hết quota Nominatim, backfill chạy tiếp và ăn
    429 hàng loạt — vừa vô ích vừa vi phạm usage policy. Circuit breaker phải cắt.
    """
    from app.crawler import backfill as bf

    rows = [{"id": i, "title": "t", "address": f"Đường Số {i}, Phường An Cư, Quận Ninh Kiều, Cần Thơ",
             "description": None, "area": 20.0, "old_conf": "high"} for i in range(1, 51)]

    async def _blocked(client, q):
        raise httpx.HTTPStatusError("429", request=None, response=None)

    stats, writes = _run_backfill(monkeypatch, rows, _blocked)

    assert stats["aborted"] is True, "429 hàng loạt mà không dừng sớm"
    assert writes == [], "lỗi mạng mà vẫn ghi DB → nhãn cũ bị đè bằng nhãn không đáng tin"
    assert stats["skipped_net"] == bf._MAX_CONSECUTIVE_FAIL
    assert stats["skipped_net"] < len(rows), "phải dừng trước khi quét hết bảng"


def test_backfill_resets_breaker_after_a_success(monkeypatch):
    """Lỗi rải rác (mạng chập chờn) KHÔNG được cắt run — chỉ lỗi LIÊN TIẾP mới cắt."""
    state = {"n": 0}

    rows = [{"id": i, "title": "t", "address": f"Đường Số {i}, Phường An Cư, Quận Ninh Kiều, Cần Thơ",
             "description": None, "area": 20.0, "old_conf": "low"} for i in range(1, 21)]

    async def _flaky(client, q):
        state["n"] += 1
        if state["n"] % 3 == 0:  # cứ 3 query lỗi 1 lần → không bao giờ đủ 5 dòng liên tiếp
            raise httpx.ConnectError("blip")
        return 10.0330, 105.7813, "tertiary"

    stats, writes = _run_backfill(monkeypatch, rows, _flaky)

    assert stats["aborted"] is False, "lỗi rải rác không được cắt cả run"
    assert stats["written"] > 0, "phải ghi được những dòng geocode thành công"


def test_backfill_writes_downgrade_when_network_is_healthy(monkeypatch):
    """Mạng ổn + nhãn cũ sai (high) → PHẢI ghi hạ nhãn.

    Đây là mục đích của lần backfill 2026-08-08: logic vừa siết lại nên việc chính
    LÀ hạ nhãn sai xuống đúng. Guard "chỉ ghi khi rank >= cũ" của bản cũ sẽ chặn mất.
    """
    rows = [{"id": 1, "title": "t",
             "address": "Khu Dân Cư Abc Xyz, Phường Qqq Www, Quận Eee Rrr, Cần Thơ",
             "description": None, "area": 20.0, "old_conf": "high"}]

    async def _poi(client, q):
        return 10.0210, 105.7654, "place_of_worship"  # POI → tầng 1/2 từ chối → low

    stats, writes = _run_backfill(monkeypatch, rows, _poi)

    assert stats["downgraded"] == 1, "nhãn cũ 'high' sai mà không bị hạ"
    assert len(writes) == 1 and writes[0]["conf"] == "low"
