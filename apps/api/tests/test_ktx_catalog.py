from pathlib import Path

import pytest

from app.ktx.catalog import KtxCatalog, room_text
from app.ktx.chat import matching_codes, select_rooms


@pytest.fixture
def catalog():
    return KtxCatalog.model_validate_json((Path(__file__).parents[1] / "app/ktx/catalog.json").read_bytes())


def test_exact_room_code_does_not_match_its_prefix(catalog):
    assert matching_codes(catalog, "KTX loại A4 có gì?") == ["A4"]
    assert matching_codes(catalog, "KTX khu A có gì?") == []


def test_pb_code_does_not_imply_area_b(catalog):
    rooms, _ = select_rooms(catalog, "KTX PB225 có thuộc khu B không?")
    assert [room.code for room in rooms] == ["PB225"]
    assert rooms[0].area_ids == []


def test_unconfirmed_prices_are_not_asserted_to_be_monthly(catalog):
    room = next(room for room in catalog.room_types if room.code == "A4")
    assert room.price_period == "unconfirmed"
    assert "chưa xác nhận kỳ tính giá" in room_text(room)
    assert "đồng/người/tháng" not in room_text(room)


def test_monthly_budget_does_not_filter_using_unconfirmed_period(catalog):
    rooms, blocked = select_rooms(catalog, "KTX 4 người dưới 100k mỗi tháng")
    assert blocked
    assert rooms
    assert all(4 in room.capacities for room in rooms)


def test_cooking_yes_no_question_does_not_exclude_non_cooking_rooms(catalog):
    rooms, _ = select_rooms(catalog, "KTX khu B 4 người năm 2025 được nấu ăn không?")
    assert rooms
    assert all(room.area_ids == ["B"] and room.cooking_allowed is False for room in rooms)
    assert all(room.price_period == "semester_3_5_months" for room in rooms)


def test_capacity_bed_and_cooking_filters_apply_together(catalog):
    rooms, _ = select_rooms(catalog, "KTX cho 6 người được nấu ăn có giường tầng")
    assert rooms
    assert all(6 in room.capacities and room.cooking_allowed and room.bed_type == "bunk" for room in rooms)


def test_map_geojson_uses_longitude_latitude_order(catalog, monkeypatch):
    import app.ktx.router as router_module
    monkeypatch.setattr(router_module, "get_catalog", lambda: catalog)
    result = router_module.map_features()
    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 2
    for feature, area in zip(result["features"], catalog.dormitories):
        assert feature["geometry"]["coordinates"] == [area.location.lng, area.location.lat]
        assert feature["properties"]["precision"] == "representative"
        assert feature["properties"]["availability"] == "unknown"
