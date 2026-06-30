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
