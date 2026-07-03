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
        # chỉ match query cấp phường chính xác (tầng 2), full-address (tầng 1) fail
        return (10.06, 105.76) if q == "An Thới, Bình Thuỷ, Cần Thơ" else None
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
