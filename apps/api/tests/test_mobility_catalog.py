"""Offline contract tests for the pinned, read-only mobility catalog."""
from collections import Counter
from importlib import import_module

import pytest
from sqlalchemy.sql.elements import TextClause

from app.mobility.contracts import BoundingBox


PINNED_PACKAGE_ID = "ccd4bb988a93e6b676d2baa49de70d7e20a9b63c64a836bd673e514c95371d35"
PINNED_CATALOG_SHA256 = "b859bab1dc66808adc897f8f2b0b858d6aa2aa3954e52fc92c8e816e533b5947"


def catalog_repo_module():
    try:
        return import_module("app.mobility.catalog_repo")
    except ModuleNotFoundError:
        pytest.fail("pinned mobility catalog repository is not implemented")


def _catalog_rows(*, package_id=PINNED_PACKAGE_ID,
                  catalog_sha256=PINNED_CATALOG_SHA256):
    rows = []
    for listing_id in range(1, 790):
        if listing_id <= 614:
            housing_type = "room"
        elif listing_id <= 782:
            housing_type = "mini_house"
        elif listing_id <= 785:
            housing_type = "studio"
        else:
            housing_type = "unknown"

        lat = 10.0 + listing_id / 10_000
        lng = 105.0 + listing_id / 10_000
        if listing_id in (788, 789):
            lat = lng = None

        row = {
            "id": listing_id,
            "title": f"Synthetic housing {listing_id}",
            "source": "synthetic_source",
            "source_id": f"source-{listing_id}",
            "source_url": f"https://example.invalid/listings/{listing_id}",
            "source_contact_url": None,
            "price": 1_500_000,
            "area": None if listing_id == 1 else 18.5,
            "address": "Synthetic address",
            "district": "Synthetic district",
            "description": "Synthetic description for repository conversion.",
            "images": [f"https://example.invalid/images/{listing_id}.jpg"],
            "housing_type": housing_type,
            "offer_kind": "RENT",
            "description_state": "PRESENT",
            "description_completeness": None,
            "description_is_partial": None,
            "unit_type_uncertain": None,
            "offer_context_uncertain": None,
            "mixed_use_possible": None,
            "lease_transfer_terms_verified": None,
            "parsed_amenities": {"wifi": True, "parking": None},
            "lat": lat,
            "lng": lng,
            "_package_id": package_id,
            "_catalog_sha256": catalog_sha256,
        }
        rows.append(row)

    rows[0]["description_is_partial"] = True
    rows[0]["lease_transfer_terms_verified"] = False
    rows[0]["mixed_use_possible"] = None
    # This is deliberately not part of the allowed position evidence.
    rows[0]["geocode_confidence"] = "high"
    return rows


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def one(self):
        assert len(self._rows) == 1
        return self._rows[0]

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)


class _FakeConnection:
    def __init__(self, engine):
        self.engine = engine

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement, parameters=None):
        assert isinstance(statement, TextClause), "queries must use sqlalchemy.text"
        sql = statement.text
        normalized = " ".join(sql.lower().split())
        params = dict(parameters or {})
        self.engine.executed.append((normalized, params))

        assert "public.catalog_handoff_v1" in normalized
        assert "public.aggregated_listings" not in normalized
        assert "source_record" not in normalized
        assert "cleaning_status" not in normalized
        assert "listing_type" not in normalized
        assert "package_id" in normalized and "catalog_sha256" in normalized
        assert "package_id" in params and "catalog_sha256" in params

        if self.engine.missing_view:
            raise RuntimeError("missing relation catalog_handoff_v1 with private detail")

        matching = [row for row in self.engine.rows
                    if row["_package_id"] == params["package_id"]
                    and row["_catalog_sha256"] == params["catalog_sha256"]]

        if "as pinned_total" in normalized:
            return _FakeResult([{
                "total": len(self.engine.rows),
                "pinned_total": len(matching),
            }])

        if "count(*) as total" in normalized:
            filtered = [row for row in matching if self._inside_bbox(row, params)]
            return _FakeResult([{"total": len(filtered)}])

        if "where v.id = :listing_id" in normalized:
            filtered = [row for row in matching
                        if row["id"] == params["listing_id"]]
            return _FakeResult([self._projection(row) for row in filtered])

        if "order by v.id" in normalized:
            filtered = [row for row in matching if self._inside_bbox(row, params)]
            filtered.sort(key=lambda row: row["id"])
            offset = params["offset"]
            limit = params["limit"]
            return _FakeResult([self._projection(row)
                                for row in filtered[offset:offset + limit]])

        pytest.fail(f"unexpected catalog query: {normalized}")

    @staticmethod
    def _inside_bbox(row, params):
        if "south" not in params:
            return True
        lat, lng = row["lat"], row["lng"]
        return (lat is not None and lng is not None
                and params["south"] <= lat <= params["north"]
                and params["west"] <= lng <= params["east"])

    @staticmethod
    def _projection(row):
        return {key: value for key, value in row.items()
                if not key.startswith("_") and key != "geocode_confidence"}


class _FakeEngine:
    def __init__(self, rows=None, *, missing_view=False):
        self.rows = list(rows if rows is not None else _catalog_rows())
        self.missing_view = missing_view
        self.connect_count = 0
        self.executed = []

    def connect(self):
        self.connect_count += 1
        return _FakeConnection(self)


def test_catalog_repo_is_lazy_and_pages_all_pinned_rows_in_id_order():
    module = catalog_repo_module()
    engine = _FakeEngine()
    repository = module.CatalogRepo(engine)

    assert engine.connect_count == 0
    pages = [repository.list_page(page=page_number, size=100)
             for page_number in range(1, 9)]
    page = pages[-1]

    assert engine.connect_count == 8
    assert all(result.total == 789 for result in pages)
    assert page.page == 8 and page.size == 100
    all_items = [item for result in pages for item in result.items]
    assert [item.id for item in all_items] == list(range(1, 790))
    assert Counter(item.housing_type for item in all_items) == {
        "room": 614, "mini_house": 168, "studio": 3, "unknown": 4,
    }
    assert sum(item.position is None for item in all_items) == 2

    for query, params in engine.executed:
        assert params["package_id"] == PINNED_PACKAGE_ID
        assert params["catalog_sha256"] == PINNED_CATALOG_SHA256
        assert "public.catalog_handoff_v1" in query
    select_queries = [query for query, _ in engine.executed
                      if "order by v.id" in query]
    assert len(select_queries) == 8
    for query in select_queries:
        assert "select *" not in query
        assert "source_record_sha256" not in query
        assert "package_id" not in query.split(" from ", 1)[0]
        assert "catalog_sha256" not in query.split(" from ", 1)[0]


def test_bbox_uses_identical_bounds_for_total_and_items():
    module = catalog_repo_module()
    engine = _FakeEngine()
    repository = module.CatalogRepo(engine)
    bbox = BoundingBox(south=10.02, west=105.02, north=10.03, east=105.03)

    page = repository.list_page(page=2, size=60, bbox=bbox)

    assert page.total == 101
    assert [item.id for item in page.items] == list(range(260, 301))
    relevant = [(query, params) for query, params in engine.executed
                if "south" in params]
    assert len(relevant) == 2
    assert all(params["south"] == 10.02 and params["north"] == 10.03
               and params["west"] == 105.02 and params["east"] == 105.03
               for _, params in relevant)
    assert any("count(*) as total" in query for query, _ in relevant)
    assert any("order by v.id" in query for query, _ in relevant)


def test_listing_conversion_keeps_catalog_kinds_flags_and_nullable_position():
    module = catalog_repo_module()
    repository = module.CatalogRepo(_FakeEngine())

    partial = repository.get_listing(1)
    assert partial is not None
    assert partial.housing_type == "room"
    assert partial.description_is_partial is True
    assert partial.lease_transfer_terms_verified is False
    assert partial.mixed_use_possible is None
    assert partial.area is None
    assert partial.position is not None
    assert partial.position.precision == "UNKNOWN"
    assert partial.position.source is None
    assert "source_record" not in partial.model_dump()
    assert partial.model_dump()["description"] == "Synthetic description for repository conversion."

    assert repository.get_listing(615).housing_type == "mini_house"
    assert repository.get_listing(783).housing_type == "studio"
    assert repository.get_listing(786).housing_type == "unknown"
    assert repository.get_listing(788).position is None
    assert repository.get_listing(789).position is None
    assert repository.get_position(788) is None
    assert repository.get_position(1).lat == pytest.approx(10.0001)
    assert repository.get_position(1).lng == pytest.approx(105.0001)


def test_missing_catalog_id_returns_none_without_aggregate_fallback():
    module = catalog_repo_module()
    engine = _FakeEngine()
    repository = module.CatalogRepo(engine)

    assert repository.get_listing(790) is None
    assert repository.get_position(790) is None
    assert all("public.catalog_handoff_v1" in query for query, _ in engine.executed)
    assert all("aggregated_listings" not in query for query, _ in engine.executed)


def test_wrong_package_or_catalog_hash_fails_closed():
    module = catalog_repo_module()
    wrong_package = _FakeEngine()
    with pytest.raises(module.CatalogUnavailable):
        module.CatalogRepo(wrong_package, package_id="wrong-package").list_page()

    wrong_hash_rows = _catalog_rows(catalog_sha256="f" * 64)
    wrong_hash = _FakeEngine(wrong_hash_rows)
    with pytest.raises(module.CatalogUnavailable):
        module.CatalogRepo(wrong_hash).get_listing(1)


def test_absent_catalog_view_is_reported_as_generic_unavailability():
    module = catalog_repo_module()
    repository = module.CatalogRepo(_FakeEngine(missing_view=True))

    with pytest.raises(module.CatalogUnavailable) as exc_info:
        repository.list_page()

    assert "private detail" not in str(exc_info.value)
    assert "missing relation" not in str(exc_info.value)
