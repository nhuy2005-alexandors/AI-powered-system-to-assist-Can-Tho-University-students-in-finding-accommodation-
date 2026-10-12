"""Offline-only guards for the real catalog acceptance harness.

All catalog rows and receipts in this file are UNIT fixtures. They are never
written as REAL_ACCEPTANCE evidence and never connect to a database or server.
"""

from __future__ import annotations

import copy
import asyncio
from dataclasses import FrozenInstanceError, replace
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
HARNESS_PATH = PROJECT_ROOT / "scripts" / "mobility_catalog_acceptance.py"
RUNTIME_CONFIG_NAME = "runtime-config.json"
SECRET_CANARY = "UNIT_SECRET_CANARY_51f00b6e"
OPERATION_ID = "2b07c5f2-84cf-47fc-90b3-e151eaa2dd7a"
PINNED_CATALOG_SHA256 = "b859bab1dc66808adc897f8f2b0b858d6aa2aa3954e52fc92c8e816e533b5947"
PINNED_ZIP_SHA256 = "25cbfca2a36adf2f93772a5e48db8f6a0a8b48e777de41668d7a4b4ee5911a4a"
CATALOG_PHASE_GATE_SHA256 = "e08c0ee7478127d6e7d514215b32f2a7463825ec25fb246ee35f2b0ee5eff3fc"
P1_PUBLIC_ARTIFACTS = (
    "docs/specs/open-mobility-migration.md",
    "docs/planning/2026-10-05-open-mobility-agent-plan.md",
    ".codex-gate.json",
)

TARGET = {
    "operation_id": OPERATION_ID,
    "host": "127.0.0.1",
    "port": 5455,
    "database": "mobility_catalog_acceptance",
    "user": "mobility_catalog_reader",
    "password": SECRET_CANARY,
    "container": "nckh-mobility-acceptance-db",
    "project": "nckh-mobility-acceptance",
    "volume": "nckh_mobility_acceptance_pgdata",
}

_BASE_CODE_PIN_PATHS = (
    "scripts/mobility_catalog_acceptance.py",
    "apps/api/tests/test_mobility_catalog_acceptance_guard.py",
    "apps/web/e2e/mobility-catalog-acceptance.cjs",
    "apps/api/app/mobility/__init__.py",
    "apps/api/app/mobility/campuses.py",
    "apps/api/app/mobility/catalog_repo.py",
    "apps/api/app/mobility/contracts.py",
    "apps/api/app/mobility/place_service.py",
    "apps/api/app/mobility/route_service.py",
    "apps/api/app/mobility/router.py",
    "apps/api/app/mobility/warnings.py",
    "apps/api/app/mobility/providers/__init__.py",
    "apps/api/app/mobility/providers/base.py",
    "apps/api/app/mobility/providers/google_places.py",
    "apps/api/app/mobility/providers/google_routes.py",
    "apps/web/src/app/map/campuses.ts",
    "apps/web/src/app/map/MapInner.tsx",
    "apps/web/src/app/map/MapShell.tsx",
    "apps/web/src/app/map/MapView.tsx",
    "apps/web/src/app/map/ResultList.tsx",
    "apps/web/src/app/map/page.tsx",
    "apps/web/src/app/api/mobility/campuses/route.ts",
    "apps/web/src/app/api/mobility/listings/route.ts",
    "apps/web/src/app/api/mobility/nearby/route.ts",
    "apps/web/src/app/api/mobility/routes/route.ts",
    "apps/web/src/components/mobility/client-api.ts",
    "apps/web/src/components/mobility/mobility-format.ts",
    "apps/web/src/components/mobility/MobilityDetails.tsx",
    "apps/web/src/components/mobility/MobilityWorkspace.tsx",
    "apps/web/src/components/mobility/OfflineCoordinateCanvas.tsx",
    "apps/web/src/lib/config.ts",
    "apps/web/src/lib/mobility-api.ts",
    "apps/web/src/lib/mobility-contracts.ts",
    "apps/api/requirements.txt",
    "apps/web/package.json",
    "apps/web/package-lock.json",
)

P1_ADDITIONAL_CODE_PIN_PATHS = (
    "docs/planning/open-mobility-provider-policy.md",
    "scripts/open_mobility_pilot.py",
    "scripts/open_mobility_tile_pilot.cjs",
    "apps/api/tests/test_open_mobility_pilot_guard.py",
    "apps/api/tests/test_open_mobility_tile_pilot_guard.py",
    "apps/api/tests/test_mobility_runtime_policy.py",
    "scripts/mobility_catalog_bootstrap.ps1",
    "apps/api/app/config.py",
    "apps/api/app/main.py",
    "apps/web/src/lib/map-provider.ts",
    "apps/web/e2e/mobility-open-map.spec.ts",
    "apps/web/e2e/mobility-offline.spec.ts",
    "apps/web/e2e/mobility-fixtures.ts",
    "apps/web/playwright.mobility.config.ts",
    "apps/api/tests/test_mobility_provider_policy.py",
    "apps/api/tests/test_mobility_ors.py",
    "apps/api/tests/test_mobility_overpass.py",
    "apps/api/tests/test_mobility_geocoder.py",
    "apps/api/tests/fixtures/open_mobility/geocoder/empty.json",
    "apps/api/tests/fixtures/open_mobility/geocoder/multiple.json",
    "apps/api/tests/fixtures/open_mobility/geocoder/single.json",
    "apps/api/tests/fixtures/open_mobility/ors/route_no_route_between.json",
    "apps/api/tests/fixtures/open_mobility/ors/route_no_route.json",
    "apps/api/tests/fixtures/open_mobility/ors/route_success.json",
    "apps/api/tests/fixtures/open_mobility/overpass/nearby_mixed.json",
    "apps/api/tests/fixtures/mobility/contracts.json",
    "apps/api/tests/fixtures/mobility/places/empty.json",
    "apps/api/tests/fixtures/mobility/places/nearby_success.json",
    "apps/api/tests/fixtures/mobility/routes/route_bus_success.json",
    "apps/api/tests/fixtures/mobility/routes/route_malformed.json",
    "apps/api/tests/fixtures/mobility/routes/route_no_route.json",
    "apps/api/tests/fixtures/mobility/routes/route_success.json",
    "apps/api/app/mobility/providers/network_policy.py",
    "apps/api/app/mobility/providers/demo_policy.py",
    "apps/api/app/mobility/providers/nominatim_geocoder.py",
    "apps/api/app/mobility/providers/open_config.py",
    "apps/api/app/mobility/providers/ors_routes.py",
    "apps/api/app/mobility/providers/overpass_places.py",
    "apps/api/app/mobility/providers/registry.py",
    "apps/web/src/components/mobility/MobilityMap.tsx",
    "apps/web/src/components/mobility/leaflet-map-provider.ts",
)

P1_REUSE_ADDITIONAL_CODE_PIN_PATHS = (
    "apps/web/src/lib/map-ui.ts",
    "apps/web/src/types/leaflet-markercluster.d.ts",
    "apps/web/e2e/map-ui-primitives.spec.ts",
    "apps/web/e2e/mobility-map-reuse.spec.ts",
    "docs/specs/open-mobility-map-reuse.md",
    "docs/planning/2026-10-05-open-mobility-map-reuse-plan.md",
)

CODE_PIN_PATHS = (
    _BASE_CODE_PIN_PATHS
    + P1_ADDITIONAL_CODE_PIN_PATHS
    + P1_REUSE_ADDITIONAL_CODE_PIN_PATHS
)

APPROVED_SOURCE_COORDINATE_VECTORS = (
    (9.974437, 105.75272, "4023f2e9680e0653", "405a702c9081c2e3"),
    (9.98187, 105.82316, "4023f6b7aa25d8d8", "405a74aea747d806"),
    (9.983268, 105.73805, "4023f76ee73e681b", "405a6f3c36113405"),
    (9.987198, 105.747986, "4023f97204295a6c", "405a6fdf00abf76a"),
    (9.9897785, 105.65885, "4023fac43f5f9160", "405a6a2a9930be0e"),
    (9.992674, 105.74607, "4023fc3fc43b2dd3", "405a6fbf9c62a1b6"),
    (9.993837, 105.799675, "4023fcd834091c08", "405a732de00d1b71"),
    (9.994971, 105.7762, "4023fd6cd6c2efd4", "405a71ad42c3c9ef"),
    (9.998691, 105.75324, "4023ff546d3f9e7c", "405a7035158b8280"),
    (9.998929, 105.694046, "4023ff739f340d4e", "405a6c6b3fe9fadb"),
    (9.998955, 105.74979, "4023ff77079e59f3", "405a6ffc8f32378b"),
    (10.000466, 105.802536, "4024003d145d8516", "405a735cbff47736"),
    (10.008509, 105.80319, "4024045b4aa9717e", "405a736777079e5a"),
    (10.010358, 105.73805, "4024054da4ce8102", "405a6f3c36113405"),
    (10.010896, 105.67058, "402405942917507f", "405a6aeac8605682"),
    (10.014643, 105.76153, "4024077f498c3b0c", "405a70bce8533b10"),
    (10.015603, 105.782524, "402407fd1dcd7061", "405a7214df8b1572"),
    (10.016784, 105.704414, "40240897e996312f", "405a6d151e75360d"),
    (10.017701, 105.73779, "402409101b003687", "405a6f37f38c5437"),
    (10.018674, 105.73978, "4024098fa376922e", "405a6f588e368f08"),
    (10.021417, 105.764755, "40240af72b452828", "405a70f1bef49cf5"),
    (10.025804, 105.77366, "40240d362e903644", "405a7183a53b8e4c"),
    (10.02848, 105.78353, "40240e94ee392e1f", "405a72255b035bd5"),
    (10.02886, 105.75899, "40240ec6bce8533b", "405a70934acaff6d"),
    (10.029048, 105.7718, "40240edf61240746", "405a71652bd3c361"),
    (10.029194, 105.796745, "40240ef284167a96", "405a72fddebd9019"),
    (10.029751, 105.72925, "40240f3b85e80bed", "405a6eac083126e9"),
    (10.029952, 105.776115, "40240f55de58e64b", "405a71abde3fbbd8"),
    (10.03045, 105.77669, "40240f972474538f", "405a71b549f94856"),
    (10.03066, 105.781235, "40240fb2aae29739", "405a71ffc115df65"),
    (10.031184, 105.75565, "40240ff759685122", "405a705c91d14e3c"),
    (10.031358, 105.74427, "4024100e27e0ef9a", "405a6fa21ea35936"),
    (10.033044, 105.7872, "402410eb24a6a876", "405a72617c1bda51"),
    (10.033709, 105.64712, "402411424e592967", "405a696a6a01259a"),
    (10.034326, 105.774734, "402411932d6ece14", "405a71953dea465a"),
    (10.036751, 105.7806, "402412d106ee30cb", "405a71f559b3d07d"),
    (10.037678, 105.78768, "4024134a87e38eb0", "405a7269595feda6"),
    (10.039889, 105.785736, "4024146c54bcf0b7", "405a72497fa5d28d"),
    (10.042314, 105.777664, "402415aa2e3c536d", "405a71c53f39d1b3"),
    (10.043121, 105.75508, "40241613f4a98aa8", "405a70533b107747"),
    (10.0437355, 105.75629, "402416647fdc5932", "405a70670e2c12ae"),
    (10.045173, 105.77522, "40241720ea5b530d", "405a719d3458cd21"),
    (10.04545, 105.76886, "4024174538ef34d7", "405a71350092ccf7"),
    (10.047769, 105.76931, "402418752da98677", "405a713c60029f17"),
    (10.04859, 105.78793, "402418e0c9d9d346", "405a726d71f36263"),
    (10.048842, 105.77458, "40241901d19157ac", "405a7192b7fe08af"),
    (10.050536, 105.77491, "402419dfdac68a93", "405a7198201cd5fa"),
    (10.058003, 105.76153, "40241db291b823c8", "405a70bce8533b10"),
    (10.063604, 105.68399, "40242090b417ca21", "405a6bc67dfe32a0"),
    (10.065894, 105.750336, "402421bcdbbe0158", "405a7005814940bc"),
    (10.071819, 105.74326, "402424c575c0767d", "405a6f9192641b33"),
    (10.072556, 105.74098, "402425260f5e41d5", "405a6f6c3760bf5d"),
    (10.098075, 105.4361, "40243236e2eb1c43", "405a5be90ff97247"),
    (10.234809, 105.418526, "40247838e29f9ce9", "405a5ac92146a1a5"),
)

EXPECTED_PUBLIC_TABLE_NAMES = tuple(
    sorted(
        (
            "_bootstrap",
            "aggregated_listings",
            "catalog_handoff_metadata",
            "contact_access_audit",
            "crawl_runs",
            "listing_contact_phones",
            "listing_feedback_contents",
            "listing_feedback_items",
            "listing_seller_relations",
            "match_requests",
            "reports",
            "roommate_profiles",
            "saved_searches",
            "seller_accounts",
            "seller_rating_observations",
            "spatial_ref_sys",
            "user_identities",
            "user_interactions",
            "users",
        )
    )
)

PUBLIC_FIELDS = (
    "id",
    "title",
    "source",
    "source_id",
    "source_url",
    "source_contact_url",
    "price",
    "area",
    "address",
    "district",
    "description",
    "images",
    "housing_type",
    "offer_kind",
    "description_state",
    "description_completeness",
    "description_is_partial",
    "unit_type_uncertain",
    "offer_context_uncertain",
    "mixed_use_possible",
    "lease_transfer_terms_verified",
    "parsed_amenities",
    "position",
)


@pytest.fixture(scope="module")
def harness():
    """Load the delivered module without turning its absence into a collection error."""
    if not HARNESS_PATH.is_file():
        return None
    name = "_mobility_catalog_acceptance_under_test"
    spec = importlib.util.spec_from_file_location(name, HARNESS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _require_harness(module):
    assert module is not None, "acceptance harness implementation is missing"
    return module


def _independent_json_sha256(value) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _independent_binary64_hex(value) -> str:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("fixture coordinate must be a finite JSON number")
    number = float(value)
    if number == 0.0:
        number = 0.0
    return struct.pack(">d", number).hex()


def _independent_positioned_members_sha256(source_rows: list[dict]) -> str:
    triples = []
    for row in source_rows:
        latitude, longitude = row["latitude"], row["longitude"]
        if latitude is None and longitude is None:
            continue
        triples.append(
            [row["id"], _independent_binary64_hex(latitude), _independent_binary64_hex(longitude)]
        )
    triples.sort(key=lambda item: item[0])
    return _independent_json_sha256(triples)


def _unit_source_rows() -> list[dict]:
    """Build an in-memory 789-row catalog with the approved aggregate profile."""
    rows = []
    for offset in range(789):
        if offset < 614:
            housing_type = "room"
        elif offset < 782:
            housing_type = "mini_house"
        elif offset < 785:
            housing_type = "studio"
        else:
            housing_type = "unknown"

        has_position = offset < 787
        rows.append(
            {
                "id": 100001 + offset,
                "title": f"Unit listing {offset + 1}",
                "source": "unit-source",
                "source_id": f"unit-{offset + 1:04d}",
                "source_url": f"https://unit.example.test/listing/{offset + 1}",
                "source_contact_url": f"https://unit.example.test/contact/{offset + 1}",
                "price": 1000000 + offset,
                "area": 20.5 + offset / 10 if offset < 153 else None,
                "address": f"Unit address {offset + 1}",
                "district": "Unit district",
                "description": f"Unit description {offset + 1}",
                "images": None if offset == 16 else [],
                "housing_type": housing_type,
                "offer_kind": "rent",
                "description_state": "partial" if offset == 0 else "complete",
                "description_completeness": "partial" if offset == 0 else "complete",
                "description_is_partial": offset == 0,
                "unit_type_uncertain": False,
                "offer_context_uncertain": False,
                "mixed_use_possible": None,
                "lease_transfer_terms_verified": False,
                "parsed_amenities": {"parking": None, "air_conditioning": True},
                "latitude": 10.0 + offset / 10000 if has_position else None,
                "longitude": 105.0 + offset / 10000 if has_position else None,
            }
        )
    return rows


def _unit_public_rows(source_rows: list[dict]) -> list[dict]:
    """Independent fixture oracle matching the documented public DTO shape."""
    output = []
    for source in source_rows:
        item = {field: source[field] for field in PUBLIC_FIELDS if field != "position"}
        if item["images"] is None:
            item["images"] = []
        latitude, longitude = source["latitude"], source["longitude"]
        item["position"] = (
            None
            if latitude is None and longitude is None
            else {
                "lat": latitude,
                "lng": longitude,
                "precision": "UNKNOWN",
                "source": None,
                "verified_at": None,
            }
        )
        output.append(item)
    return output


def _unit_code_pins() -> dict[str, str]:
    return {path: hashlib.sha256(path.encode("utf-8")).hexdigest() for path in CODE_PIN_PATHS}


def _synthetic_pin_project(tmp_path: Path, module, monkeypatch) -> Path:
    project_root = tmp_path / "synthetic-project"
    project_root.mkdir()
    monkeypatch.setattr(
        module,
        "CODE_PIN_FILES",
        tuple(path for path in CODE_PIN_PATHS if path != "scripts/mobility_catalog_acceptance.py"),
    )
    paths = set(CODE_PIN_PATHS) | set(module.CODE_PIN_FILES)
    paths.add("scripts/mobility_catalog_acceptance.py")
    for relative in sorted(paths):
        candidate = project_root / Path(relative)
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_bytes(("UNIT_PIN:" + relative).encode("utf-8"))
    for relative_root in module.CODE_PIN_ROOTS:
        (project_root / Path(relative_root)).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(module, "PROJECT_ROOT", project_root)
    return project_root


def _synthetic_evidence_workspace(
    tmp_path: Path, module, monkeypatch, *, gate_bytes: bytes
) -> tuple[Path, Path]:
    project_root = _synthetic_pin_project(tmp_path, module, monkeypatch)
    artifact_paths = set(P1_PUBLIC_ARTIFACTS) | set(module.PUBLIC_ARTIFACTS)
    for relative in sorted(artifact_paths):
        candidate = project_root / Path(relative)
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_bytes(("UNIT_ARTIFACT:" + relative).encode("utf-8"))
    (project_root / ".codex-gate.json").write_bytes(gate_bytes)

    catalog_path = tmp_path / "unit-source-catalog.jsonl"
    zip_path = tmp_path / "unit-source-package.zip"
    catalog_path.write_bytes(b"UNIT CATALOG BYTES")
    zip_path.write_bytes(b"UNIT PACKAGE BYTES")
    monkeypatch.setattr(module, "SOURCE_CATALOG_PATH", catalog_path)
    monkeypatch.setattr(module, "SOURCE_ZIP_PATH", zip_path)
    monkeypatch.setattr(module, "SOURCE_CATALOG_SHA256", hashlib.sha256(catalog_path.read_bytes()).hexdigest())
    monkeypatch.setattr(module, "SOURCE_ZIP_SHA256", hashlib.sha256(zip_path.read_bytes()).hexdigest())

    runtime_dir = tmp_path / "synthetic-runtime"
    runtime_dir.mkdir()
    (runtime_dir / module.RUNTIME_CONFIG_NAME).write_text(
        json.dumps(TARGET), encoding="utf-8"
    )
    return project_root, runtime_dir


def _file_pin_hashes(module, project_root: Path) -> dict[str, str]:
    return {
        relative: hashlib.sha256((project_root / Path(relative)).read_bytes()).hexdigest()
        for relative in module.discover_source_pin_paths(project_root)
    }


def _unit_receipt(source_rows: list[dict], code_pins: dict[str, str]) -> tuple[dict, dict]:
    public_rows = _unit_public_rows(source_rows)
    expected_ids = sorted(row["id"] for row in source_rows)
    expected_public_hash = _independent_json_sha256(public_rows)
    browser = {
        "schema_version": 2,
        "status": "REAL_CATALOG_BROWSER_VERIFIED",
        "evidence_kind": "REAL_POSTGRES_REAL_CATALOG",
        "operation_id": OPERATION_ID,
        "expected_public_data_sha256": expected_public_hash,
        "actual_ids_sha256": _independent_json_sha256(expected_ids),
        "api_origin": "http://127.0.0.1:8032",
        "ui_origin": "http://127.0.0.1:3032",
        "source_catalog_count": 789,
        "unique_listing_count": 789,
        "missing_position_count": 2,
        "positioned_listing_count": 787,
        "actual_positioned_members_sha256": _independent_positioned_members_sha256(source_rows),
        "visible_checks": {
            "original_titles": True,
            "null_area": True,
            "partial_description": True,
            "withheld_description": True,
            "contact_href": True,
            "missing_position_selectable": True,
            "missing_position_has_no_pin": True,
            "missing_position_route_disabled": True,
            "actual_cluster_membership": True,
        },
        "external_attempts": 0,
    }
    table_digests = {
        f"public.{name}": {"row_count": 789, "sha256": hashlib.sha256(name.encode()).hexdigest()}
        for name in EXPECTED_PUBLIC_TABLE_NAMES
    }
    operation = {
        "operation_id": OPERATION_ID,
        "container": "nckh-mobility-acceptance-db",
        "project": "nckh-mobility-acceptance",
        "volume": "nckh_mobility_acceptance_pgdata",
        "host": "127.0.0.1",
        "port": 5455,
        "database": "mobility_catalog_acceptance",
        "role": "mobility_catalog_reader",
        "expected_public_table_names": EXPECTED_PUBLIC_TABLE_NAMES,
    }
    receipt = {
        "schema_version": 1,
        "operation_id": OPERATION_ID,
        "status": "REAL_CATALOG_POSTGRES_UI_VERIFIED",
        "evidence_kind": "REAL_POSTGRES_REAL_CATALOG",
        "completed_at": "2026-10-04T04:00:00Z",
        "target": {
            key: value
            for key, value in operation.items()
            if key not in {"operation_id", "expected_public_table_names"}
        },
        "image_id": "sha256:dcea513d8f8c0bd2b314bfaa672d1bb3a91d100c401afe34f139dcd3c5869bdd",
        "source_catalog_sha256": PINNED_CATALOG_SHA256,
        "source_zip_sha256": PINNED_ZIP_SHA256,
        "code_sha256": copy.deepcopy(code_pins),
        "spec_sha256": "c" * 64,
        "plan_sha256": "d" * 64,
        "gate_sha256": "e" * 64,
        "runtime_config_sha256": "f" * 64,
        "source_catalog_count": 789,
        "actual_ids_sha256": _independent_json_sha256(expected_ids),
        "public_dto_sha256": expected_public_hash,
        "table_digests_before": copy.deepcopy(table_digests),
        "table_digests_after": copy.deepcopy(table_digests),
        "public_table_manifest": [f"public.{name}" for name in EXPECTED_PUBLIC_TABLE_NAMES],
        "view_digest_before": {"row_count": 789, "sha256": "1" * 64},
        "view_digest_after": {"row_count": 789, "sha256": "1" * 64},
        "checks": {f"AC{index}": True for index in range(1, 7)},
        "readonly_probe": {"transaction_read_only": True, "dml_rejected": True},
        "counts": {
            "http": {"rows": 789, "unique_ids": 789, "pages": 8},
            "api": {"rows": 789, "unique_ids": 789, "pages": 8},
            "browser": {"rows": 789, "unique_ids": 789, "missing_positions": 2},
        },
        "browser": browser,
        "browser_receipt_sha256": _independent_json_sha256(browser),
        "screenshot_sha256": "2" * 64,
        "external_attempts": 0,
    }
    return receipt, operation


def _unit_cluster_case(mutation: str | None = None) -> tuple[list[dict], object]:
    source_rows = _unit_source_rows()
    expected_rows = _unit_public_rows(source_rows)
    members = [
        {
            "id": row["id"],
            "lat": row["position"]["lat"],
            "lng": row["position"]["lng"],
        }
        for row in expected_rows
        if row["position"] is not None
    ]
    members.reverse()
    snapshot = {"generation": 7, "state": "READY", "members": members}

    if mutation == "missing-member":
        snapshot["members"].pop()
    elif mutation == "extra-member":
        snapshot["members"].append({"id": 999999, "lat": 10.5, "lng": 105.5})
    elif mutation == "duplicate-id":
        snapshot["members"][-1]["id"] = snapshot["members"][-2]["id"]
    elif mutation == "wrong-id":
        snapshot["members"][-1]["id"] = 999999
    elif mutation == "wrong-coordinate":
        snapshot["members"][-1]["lat"] += 0.001
    elif mutation == "string-id":
        snapshot["members"][-1]["id"] = str(snapshot["members"][-1]["id"])
    elif mutation == "boolean-coordinate":
        snapshot["members"][-1]["lat"] = True
    elif mutation == "string-coordinate":
        snapshot["members"][-1]["lng"] = str(snapshot["members"][-1]["lng"])
    elif mutation == "extra-member-key":
        snapshot["members"][-1]["marker_count"] = 1
    elif mutation == "extra-top-key":
        snapshot["claimed_count"] = 787
    elif mutation == "array-top-level":
        snapshot = snapshot["members"]
    elif mutation == "wrong-state":
        snapshot["state"] = "EMPTY"
    elif mutation == "negative-generation":
        snapshot["generation"] = -1
    elif mutation == "boolean-generation":
        snapshot["generation"] = True
    elif mutation == "latitude-out-of-range":
        snapshot["members"][-1]["lat"] = 91
    elif mutation is not None:
        raise AssertionError(f"unknown cluster mutation: {mutation}")
    return expected_rows, snapshot


def _id980_case(mutation: str | None = None) -> tuple[list[dict], dict]:
    withheld = {
        "id": 980,
        "title": "Unit withheld listing 980",
        "description": "",
        "description_state": "WITHHELD_UNSAFE_CONTACT",
        "description_completeness": "UNKNOWN",
        "description_is_partial": True,
        "source_url": "https://unit.example.test/listing/980",
        "source_contact_url": "https://unit.example.test/contact/980",
    }
    alternate = {
        "id": 981,
        "title": "Unit alternate withheld listing",
        "description": None,
        "description_state": "WITHHELD_UNSAFE_CONTACT",
        "description_completeness": "UNKNOWN",
        "description_is_partial": True,
        "source_url": "https://unit.example.test/listing/981",
        "source_contact_url": "https://unit.example.test/contact/981",
    }
    rows = [withheld, alternate]
    evidence = {
        "id": 980,
        "ariaPressed": True,
        "title": withheld["title"],
        "detailText": "Mô tả chưa đầy đủ · Tin đăng chưa có mô tả.",
        "paragraphs": ["Tin đăng chưa có mô tả."],
        "sourceLinkHref": withheld["source_url"],
        "contactLinkHref": withheld["source_contact_url"],
    }
    if mutation == "alternate-withheld-row":
        evidence["id"] = 981
        evidence["title"] = alternate["title"]
        evidence["sourceLinkHref"] = alternate["source_url"]
        evidence["contactLinkHref"] = alternate["source_contact_url"]
    elif mutation == "wrong-title":
        evidence["title"] = "another source title"
    elif mutation == "not-selected":
        evidence["ariaPressed"] = False
    elif mutation == "wrong-source-link":
        evidence["sourceLinkHref"] = alternate["source_url"]
    elif mutation == "wrong-contact-link":
        evidence["contactLinkHref"] = alternate["source_contact_url"]
    elif mutation == "missing-partial-label":
        evidence["detailText"] = "Tin đăng chưa có mô tả."
    elif mutation == "wrong-fallback-description":
        evidence["paragraphs"] = ["Một mô tả khác."]
    elif mutation == "unsafe-source-url":
        withheld["source_url"] = "javascript:alert(1)"
        evidence["sourceLinkHref"] = None
    elif mutation == "wrong-withheld-state":
        withheld["description_state"] = "PARTIAL"
    elif mutation == "nonempty-withheld-description":
        withheld["description"] = "should not be visible"
    elif mutation == "duplicate-id980":
        rows.append(copy.deepcopy(withheld))
    elif mutation == "unsafe-contact-url":
        withheld["source_contact_url"] = "javascript:alert(1)"
        evidence["contactLinkHref"] = withheld["source_contact_url"]
    elif mutation == "contact-link-present-when-unsafe":
        withheld["source_contact_url"] = None
    elif mutation is not None:
        raise AssertionError(f"unknown ID 980 mutation: {mutation}")
    return rows, evidence


def _run_node_helper(tmp_path: Path, program: str, payload: object) -> subprocess.CompletedProcess[str]:
    node = shutil.which("node")
    assert node is not None, "local Node.js is required for offline browser-harness guard tests"
    helper_path = PROJECT_ROOT / "apps/web/e2e/mobility-catalog-acceptance.cjs"
    payload_path = tmp_path / "unit-browser-helper-input.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return subprocess.run(
        [node, "-e", program, str(helper_path), str(payload_path)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def _assert_generic_cli_failure(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 1
    assert result.stderr == ""
    lines = result.stdout.splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {
        "status": "FAIL",
        "code": "ACCEPTANCE_NOT_VERIFIED",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("port", 5432),
        ("port", 5454),
        ("host", "198.51.100.10"),
        ("database", "postgres"),
        ("user", "nckh_handoff"),
    ],
)
def test_wrong_target_is_rejected_before_engine_factory_and_redacts_secret(
    harness, field, value
):
    module = _require_harness(harness)
    config = dict(TARGET)
    config[field] = value
    engine_calls = []

    def engine_factory(*args, **kwargs):
        engine_calls.append((args, kwargs))
        raise AssertionError("invalid target reached engine factory")

    with pytest.raises(ValueError, match=r"^Invalid acceptance configuration\.$") as error:
        module.connect_readonly(config, engine_factory=engine_factory)

    assert engine_calls == []
    assert SECRET_CANARY not in str(error.value)


@pytest.mark.parametrize(
    "edit",
    [
        lambda config: config.pop("password"),
        lambda config: config.__setitem__("unexpected", SECRET_CANARY),
        lambda config: config.__setitem__("port", True),
        lambda config: config.__setitem__("operation_id", OPERATION_ID.upper()),
    ],
    ids=["missing-key", "extra-secret-key", "bool-is-not-int-port", "noncanonical-uuid"],
)
def test_runtime_config_has_exact_keys_and_strict_types_before_engine_factory(
    harness, edit
):
    module = _require_harness(harness)
    config = dict(TARGET)
    edit(config)
    engine_calls = []

    with pytest.raises(ValueError, match=r"^Invalid acceptance configuration\.$"):
        module.connect_readonly(
            config,
            engine_factory=lambda *args, **kwargs: engine_calls.append((args, kwargs)),
        )

    assert engine_calls == []


def test_runtime_config_is_frozen_and_password_is_hidden_from_repr(harness):
    module = _require_harness(harness)
    config = module.validate_runtime_config(dict(TARGET))

    assert isinstance(config, module.RuntimeConfig)
    assert config.operation_id == OPERATION_ID
    assert config.password == SECRET_CANARY
    assert SECRET_CANARY not in repr(config)
    with pytest.raises(FrozenInstanceError):
        config.port = 5432


def test_forged_runtime_config_dataclass_is_revalidated_before_engine_factory(harness):
    module = _require_harness(harness)
    safe = module.validate_runtime_config(dict(TARGET))
    forged = replace(safe, port=5432)
    engine_calls = []

    with pytest.raises(ValueError, match=r"^Invalid acceptance configuration\.$"):
        module.connect_readonly(
            forged,
            engine_factory=lambda *args, **kwargs: engine_calls.append((args, kwargs)),
        )

    assert engine_calls == []


def test_valid_config_uses_structured_postgres_url_and_readonly_repeatable_read(harness):
    module = _require_harness(harness)
    captured = {}
    expected_engine = object()

    def engine_factory(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return expected_engine

    engine = module.connect_readonly(dict(TARGET), engine_factory=engine_factory)

    assert engine is expected_engine
    url = captured["url"]
    assert url.drivername == "postgresql+psycopg"
    assert url.username == "mobility_catalog_reader"
    assert url.password == SECRET_CANARY
    assert url.host == "127.0.0.1"
    assert url.port == 5455
    assert url.database == "mobility_catalog_acceptance"
    assert captured["kwargs"]["connect_args"]["connect_timeout"] == 2
    assert captured["kwargs"]["connect_args"]["options"] == "-c statement_timeout=5000 -c lock_timeout=2000"
    assert captured["kwargs"]["isolation_level"] == "REPEATABLE READ"
    assert captured["kwargs"]["execution_options"]["postgresql_readonly"] is True


class _FakeResult:
    def __init__(self, *, scalar=None, mapping=None):
        self._scalar = scalar
        self._mapping = mapping

    def scalar_one(self):
        return self._scalar

    def mappings(self):
        return self

    def one(self):
        return self._mapping


class _FakeOrigError(Exception):
    def __init__(self, sqlstate=None):
        super().__init__("unit database refusal")
        self.sqlstate = sqlstate


class _FakeDbError(Exception):
    def __init__(self, sqlstate=None):
        super().__init__("unit database refusal")
        self.orig = _FakeOrigError(sqlstate)


class _FakeDmlConnection:
    def __init__(self, *, failure_state="25006", identity=None, allow_update=False):
        self.failure_state = failure_state
        self.identity = identity or {
            "database_name": "mobility_catalog_acceptance",
            "role_name": "mobility_catalog_reader",
            "read_only": "on",
        }
        self.allow_update = allow_update
        self.update_attempted = False
        self.rollback_count = 0
        self.closed = False

    def exec_driver_sql(self, statement):
        if "current_database" in statement:
            return _FakeResult(mapping=self.identity)
        if statement == "SHOW transaction_read_only":
            return _FakeResult(scalar=self.identity["read_only"])
        return _FakeResult()

    def execute(self, statement):
        statement_text = str(statement)
        if statement_text.startswith("UPDATE "):
            self.update_attempted = True
            if self.allow_update:
                return _FakeResult()
            raise _FakeDbError(self.failure_state)
        return _FakeResult()

    def rollback(self):
        self.rollback_count += 1

    def close(self):
        self.closed = True


class _FakeDmlEngine:
    def __init__(self, connection):
        self.connection = connection

    def connect(self):
        return self.connection


@pytest.mark.parametrize("sqlstate", ["25006", "42501"])
def test_dml_probe_accepts_only_readonly_or_permission_denial_and_cleans_up(harness, sqlstate):
    module = _require_harness(harness)
    connection = _FakeDmlConnection(failure_state=sqlstate)

    assert module._readonly_dml_probe(_FakeDmlEngine(connection)) is None
    assert connection.update_attempted
    assert connection.rollback_count == 1
    assert connection.closed


@pytest.mark.parametrize("sqlstate", [None, "08006", "42601"])
def test_dml_probe_rejects_disconnect_syntax_and_unknown_errors(harness, sqlstate):
    module = _require_harness(harness)
    connection = _FakeDmlConnection(failure_state=sqlstate)

    with pytest.raises(ValueError, match=r"^Acceptance reader DML refusal probe failed\.$"):
        module._readonly_dml_probe(_FakeDmlEngine(connection))
    assert connection.update_attempted
    assert connection.rollback_count == 1
    assert connection.closed


def test_dml_probe_rejects_unexpected_update_success_and_rolls_back(harness):
    module = _require_harness(harness)
    connection = _FakeDmlConnection(allow_update=True)

    with pytest.raises(ValueError, match=r"^Acceptance reader DML refusal probe failed\.$"):
        module._readonly_dml_probe(_FakeDmlEngine(connection))
    assert connection.update_attempted
    assert connection.rollback_count == 1
    assert connection.closed


@pytest.mark.parametrize(
    "identity",
    [
        {"database_name": "postgres", "role_name": "mobility_catalog_reader", "read_only": "on"},
        {"database_name": "mobility_catalog_acceptance", "role_name": "nckh_handoff", "read_only": "on"},
        {"database_name": "mobility_catalog_acceptance", "role_name": "mobility_catalog_reader", "read_only": "off"},
    ],
)
def test_dml_probe_checks_database_role_and_readonly_mode_before_update(harness, identity):
    module = _require_harness(harness)
    connection = _FakeDmlConnection(identity=identity)

    with pytest.raises(ValueError):
        module._readonly_dml_probe(_FakeDmlEngine(connection))
    assert not connection.update_attempted
    assert connection.rollback_count == 1
    assert connection.closed


def test_postgres_record_digest_sorts_utf8_bytes_and_preserves_null_text(harness):
    module = _require_harness(harness)
    records = ['{"id":2,"area":null,"title":"Cần Thơ"}', '{"id":1,"area":null}']
    encoded = sorted(record.encode("utf-8") for record in records)
    expected = hashlib.sha256()
    for raw in encoded:
        expected.update(str(len(raw)).encode("ascii"))
        expected.update(b":")
        expected.update(raw)
        expected.update(b"\n")

    assert module.canonical_records_sha256(records) == expected.hexdigest()
    assert module.canonical_records_sha256(list(reversed(records))) == expected.hexdigest()
    with pytest.raises((TypeError, ValueError)):
        module.canonical_records_sha256([records[0], None])


def test_canonical_json_digest_is_key_order_independent_and_rejects_nan(harness):
    module = _require_harness(harness)
    left = {"title": "Cần Thơ", "area": None, "id": 100001}
    right = {"id": 100001, "area": None, "title": "Cần Thơ"}
    assert module.canonical_json_sha256(left) == _independent_json_sha256(right)
    assert module.canonical_json_sha256(left) == module.canonical_json_sha256(right)
    with pytest.raises((TypeError, ValueError)):
        module.canonical_json_sha256({"not_finite": float("nan")})


def test_projection_checks_all_789_ids_public_fields_nulls_and_fixed_aggregates(harness):
    module = _require_harness(harness)
    source_rows = _unit_source_rows()
    actual_rows = _unit_public_rows(source_rows)

    metrics = module.validate_catalog_projection(source_rows, actual_rows)

    assert metrics["catalog_count"] == 789
    assert metrics["housing_type_counts"] == {
        "room": 614,
        "mini_house": 168,
        "studio": 3,
        "unknown": 4,
    }
    assert metrics["area_value_count"] == 153
    assert metrics["area_null_count"] == 636
    assert metrics["position_count"] == 787
    assert metrics["position_null_count"] == 2
    assert actual_rows[0]["id"] == 100001
    assert actual_rows[-1]["id"] == 100789
    assert actual_rows[16]["images"] == []
    assert actual_rows[152]["area"] is not None
    assert actual_rows[153]["area"] is None
    assert actual_rows[-2]["position"] is None
    assert actual_rows[-1]["position"] is None
    assert set(actual_rows[0]) == set(PUBLIC_FIELDS)


@pytest.mark.parametrize(
    "mutation",
    [
        "drop-row",
        "replace-id",
        "change-title",
        "change-contact-href",
        "erase-null-area",
        "reorder-rows",
        "add-unapproved-field",
    ],
)
def test_projection_rejects_wrong_counts_membership_fields_nulls_and_order(harness, mutation):
    module = _require_harness(harness)
    source_rows = _unit_source_rows()
    actual_rows = _unit_public_rows(source_rows)

    if mutation == "drop-row":
        actual_rows.pop()
    elif mutation == "replace-id":
        actual_rows[1]["id"] = 900001
    elif mutation == "change-title":
        actual_rows[10]["title"] += " changed"
    elif mutation == "change-contact-href":
        actual_rows[10]["source_contact_url"] = "https://wrong.example.test/"
    elif mutation == "erase-null-area":
        actual_rows[153]["area"] = 1.0
    elif mutation == "reorder-rows":
        actual_rows.reverse()
    else:
        actual_rows[10]["private_debug"] = "must not be public"

    with pytest.raises(ValueError, match=r"^Catalog acceptance mismatch\.$"):
        module.validate_catalog_projection(source_rows, actual_rows)


def test_real_receipt_unit_fixture_binds_expected_data_operation_and_exact_pin_set(harness):
    module = _require_harness(harness)
    source_rows = _unit_source_rows()
    code_pins = _unit_code_pins()
    receipt, operation = _unit_receipt(source_rows, code_pins)

    result = module.validate_real_receipt_document(
        receipt,
        expected_source_rows=source_rows,
        expected_code_pin_hashes=code_pins,
        expected_operation=operation,
    )

    assert result is None


def test_browser_receipt_v2_binds_actual_cluster_membership_and_closed_visible_check(harness):
    module = _require_harness(harness)
    source_rows = _unit_source_rows()
    code_pins = _unit_code_pins()
    receipt, operation = _unit_receipt(source_rows, code_pins)

    assert module.validate_real_receipt_document(
        receipt,
        expected_source_rows=source_rows,
        expected_code_pin_hashes=code_pins,
        expected_operation=operation,
    ) is None


@pytest.mark.parametrize(
    "mutation",
    [
        "browser-v1",
        "browser-extra-field",
        "positioned-count-bool",
        "positioned-count-wrong",
        "positioned-digest-wrong",
        "positioned-digest-uppercase",
        "missing-cluster-visible-check",
        "false-cluster-visible-check",
    ],
)
def test_browser_receipt_v2_rejects_open_or_untrusted_cluster_claims(harness, mutation):
    module = _require_harness(harness)
    source_rows = _unit_source_rows()
    code_pins = _unit_code_pins()
    receipt, operation = _unit_receipt(source_rows, code_pins)
    module.validate_real_receipt_document(receipt, source_rows, code_pins, operation)

    browser = receipt["browser"]
    if mutation == "browser-v1":
        browser["schema_version"] = 1
    elif mutation == "browser-extra-field":
        browser["claimed_cluster_source"] = "receipt-input"
    elif mutation == "positioned-count-bool":
        browser["positioned_listing_count"] = True
    elif mutation == "positioned-count-wrong":
        browser["positioned_listing_count"] = 786
    elif mutation == "positioned-digest-wrong":
        browser["actual_positioned_members_sha256"] = "0" * 64
    elif mutation == "positioned-digest-uppercase":
        browser["actual_positioned_members_sha256"] = "A" * 64
    elif mutation == "missing-cluster-visible-check":
        browser["visible_checks"].pop("actual_cluster_membership")
    elif mutation == "false-cluster-visible-check":
        browser["visible_checks"]["actual_cluster_membership"] = False
    else:
        raise AssertionError(f"unknown browser receipt mutation: {mutation}")
    receipt["browser_receipt_sha256"] = _independent_json_sha256(browser)

    with pytest.raises(ValueError, match=r"^Acceptance receipt verification failed\.$"):
        module.validate_real_receipt_document(receipt, source_rows, code_pins, operation)


def test_code_pin_discovery_covers_every_mobility_ui_client_proxy_and_manifest(harness):
    module = _require_harness(harness)
    assert tuple(module.discover_source_pin_paths(PROJECT_ROOT)) == tuple(sorted(CODE_PIN_PATHS))


def test_final_open_mobility_artifacts_and_catalog_gate_digest_are_independently_pinned(harness):
    module = _require_harness(harness)
    assert getattr(module, "PUBLIC_ARTIFACTS", None) == P1_PUBLIC_ARTIFACTS
    assert getattr(module, "CATALOG_PHASE_GATE_SHA256", None) == CATALOG_PHASE_GATE_SHA256
    assert set(P1_REUSE_ADDITIONAL_CODE_PIN_PATHS).isdisjoint(module.PUBLIC_ARTIFACTS)
    assert set(P1_REUSE_ADDITIONAL_CODE_PIN_PATHS).issubset(CODE_PIN_PATHS)


def test_p4_catalog_template_has_independent_reviewed_content_binding(harness):
    expected = "e08c0ee7478127d6e7d514215b32f2a7463825ec25fb246ee35f2b0ee5eff3fc"
    template = PROJECT_ROOT / ".codex-open-mobility-catalog-gate.json"
    assert hashlib.sha256(template.read_bytes()).hexdigest() == expected
    assert harness.CATALOG_PHASE_GATE_SHA256 == expected


def test_p4_gate_builds_after_all_next_dev_checks_and_before_receipt_verification():
    gate = json.loads((PROJECT_ROOT / ".codex-gate.json").read_text(encoding="utf-8"))
    assert [check["name"] for check in gate["checks"]] == [
        "mobility_disabled_map_browser",
        "mobility_local_tile_browser",
        "p3_mobility_and_acceptance_offline",
        "p3_catalog_browser_harness_syntax",
        "mobility_open_and_regression_browser",
        "mobility_web_build",
        "catalog789_real_acceptance_receipt",
    ]


@pytest.mark.parametrize("web", [False, True])
def test_p4_child_docker_config_ignores_inherited_auth_config(harness, monkeypatch, web):
    monkeypatch.setenv("DOCKER_CONFIG", "UNIT_UNTRUSTED_AUTH_CONFIG")
    monkeypatch.setenv("DOCKER_HOST", "tcp://unit.example.test:2375")
    env = harness._minimal_child_env(web=web)
    expected = str(PROJECT_ROOT / ".superpowers/sdd/2026-10-05-open-mobility-agent-plan/docker-readonly-config")
    assert env.get("DOCKER_CONFIG") == expected
    assert "DOCKER_HOST" not in env
    assert "UNIT_UNTRUSTED_AUTH_CONFIG" not in env.values()


def test_p4_bootstrap_child_environment_keeps_docker_compose_plugin_discovery():
    bootstrap = (PROJECT_ROOT / "scripts" / "mobility_catalog_bootstrap.ps1").read_text(
        encoding="utf-8"
    )
    match = re.search(
        r"foreach\s*\(\$key\s+in\s+@\(([^)]*)\)\)", bootstrap, re.IGNORECASE
    )
    assert match is not None, "bootstrap child environment allowlist must remain explicit"
    preserved = tuple(re.findall(r"'([^']+)'", match.group(1)))
    assert preserved == (
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
        "COMSPEC",
        "PATHEXT",
        "ProgramFiles",
    )


@pytest.mark.parametrize("entrypoint", ["create", "verify-receipt"])
def test_wrong_catalog_gate_is_rejected_before_creation_or_receipt_verification(
    harness, monkeypatch, tmp_path, entrypoint
):
    module = _require_harness(harness)
    _, runtime_dir = _synthetic_evidence_workspace(
        tmp_path, module, monkeypatch, gate_bytes=b'{"phase":"unit-wrong"}'
    )
    operation_calls = []

    def forbidden_operation(name):
        def reject(*args, **kwargs):
            operation_calls.append(name)
            raise ValueError("unit operation reached")
        return reject

    for name in (
        "_pinned_public_table_names",
        "_read_source_catalog",
        "_workspace_evidence_hashes",
        "_verify_expected_public_file",
        "_inspect_clone_identity",
        "connect_readonly",
    ):
        monkeypatch.setattr(module, name, forbidden_operation(name))

    evidence_reads = []
    original_read_bytes = Path.read_bytes
    original_read_text = Path.read_text
    protected_paths = {
        (runtime_dir / module.RUNTIME_CONFIG_NAME).resolve(),
        (runtime_dir / module.REAL_ACCEPTANCE_NAME).resolve(),
        (runtime_dir / module.BROWSER_RECEIPT_NAME).resolve(),
        (runtime_dir / module.EXPECTED_PUBLIC_DATA_NAME).resolve(),
    }

    def guarded_read_bytes(path):
        if path.resolve() in protected_paths:
            evidence_reads.append(path.name)
            raise ValueError("unit receipt evidence read reached")
        return original_read_bytes(path)

    def guarded_read_text(path, *args, **kwargs):
        if path.resolve() in protected_paths:
            evidence_reads.append(path.name)
            raise ValueError("unit receipt evidence read reached")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    if entrypoint == "create":
        monkeypatch.setattr(module, "_runtime_directory", lambda path: Path(path))
        action = lambda: module._verify_acceptance(runtime_dir)
    else:
        (runtime_dir / module.REAL_ACCEPTANCE_NAME).write_text("{}", encoding="utf-8")
        action = lambda: module._verify_receipt(runtime_dir)

    with pytest.raises(ValueError) as error:
        action()
    assert str(error.value) == "Acceptance catalog gate verification failed."
    assert operation_calls == []
    assert evidence_reads == []


@pytest.mark.parametrize("relative_path", P1_ADDITIONAL_CODE_PIN_PATHS)
def test_every_new_final_pin_mutation_and_missing_file_invalidates_unit_receipt(
    harness, monkeypatch, tmp_path, relative_path
):
    module = _require_harness(harness)
    project_root = _synthetic_pin_project(tmp_path, module, monkeypatch)
    pins = module.discover_source_pin_paths(project_root)
    assert tuple(pins) == tuple(sorted(CODE_PIN_PATHS))
    assert relative_path in pins

    target = project_root / Path(relative_path)
    original = target.read_bytes()
    target.unlink()
    with pytest.raises(ValueError, match="Acceptance source pins are incomplete"):
        module.discover_source_pin_paths(project_root)
    target.write_bytes(original)

    source_rows = _unit_source_rows()
    before = _file_pin_hashes(module, project_root)
    receipt, operation = _unit_receipt(source_rows, before)
    module.validate_real_receipt_document(receipt, source_rows, before, operation)
    target.write_bytes(original + b"\nUNIT MUTATION\n")
    after = _file_pin_hashes(module, project_root)
    assert after[relative_path] != before[relative_path]
    with pytest.raises(ValueError, match=r"^Acceptance receipt verification failed\.$"):
        module.validate_real_receipt_document(receipt, source_rows, after, operation)


@pytest.mark.parametrize("relative_path", P1_REUSE_ADDITIONAL_CODE_PIN_PATHS)
def test_each_map_reuse_pin_missing_or_changed_invalidates_unit_receipt(
    harness, monkeypatch, tmp_path, relative_path
):
    module = _require_harness(harness)
    project_root = _synthetic_pin_project(tmp_path, module, monkeypatch)
    before_paths = module.discover_source_pin_paths(project_root)
    assert tuple(before_paths) == tuple(sorted(CODE_PIN_PATHS))
    assert relative_path in before_paths

    target = project_root / Path(relative_path)
    original = target.read_bytes()
    target.unlink()
    with pytest.raises(ValueError, match="Acceptance source pins are incomplete"):
        module.discover_source_pin_paths(project_root)
    target.write_bytes(original)

    source_rows = _unit_source_rows()
    before = _file_pin_hashes(module, project_root)
    receipt, operation = _unit_receipt(source_rows, before)
    module.validate_real_receipt_document(receipt, source_rows, before, operation)
    target.write_bytes(original + b"\nUNIT MAP REUSE PIN MUTATION\n")
    after = _file_pin_hashes(module, project_root)
    assert after[relative_path] != before[relative_path]
    with pytest.raises(ValueError, match=r"^Acceptance receipt verification failed\.$"):
        module.validate_real_receipt_document(receipt, source_rows, after, operation)


@pytest.mark.parametrize("web", [False, True])
def test_minimal_child_environment_forces_open_provider_and_tile_knobs_off(
    harness, monkeypatch, web
):
    module = _require_harness(harness)
    hostile = {
        "GOOGLE_MAPS_ENABLED": "true",
        "MOBILITY_LIVE_ENABLED": "true",
        "MOBILITY_ROUTING_PROVIDER": "ors",
        "MOBILITY_PLACES_PROVIDER": "osm_overpass",
        "MOBILITY_GEOCODER_PROVIDER": "nominatim",
        "MOBILITY_ORS_API_KEY": SECRET_CANARY,
        "MOBILITY_ORS_BASE_URL": "https://unit.example.test/ors",
        "MOBILITY_OVERPASS_URL": "https://unit.example.test/overpass",
        "MOBILITY_NOMINATIM_URL": "https://unit.example.test/geocode",
        "MOBILITY_TILES_ENABLED": "true",
        "MOBILITY_TILE_URL": "https://unit.example.test/{z}/{x}/{y}.png",
        "MOBILITY_TILE_ATTRIBUTION": "unit attribution",
        "MOBILITY_ALLOWED_TILE_ORIGIN": "https://unit.example.test",
    }
    for name, value in hostile.items():
        monkeypatch.setenv(name, value)

    child_env = module._minimal_child_env(web=web)
    forced_off = {
        "GOOGLE_MAPS_ENABLED": "false",
        "MOBILITY_LIVE_ENABLED": "false",
        "MOBILITY_ROUTING_PROVIDER": "disabled",
        "MOBILITY_PLACES_PROVIDER": "disabled",
        "MOBILITY_GEOCODER_PROVIDER": "disabled",
        "MOBILITY_ORS_API_KEY": "",
        "MOBILITY_ORS_BASE_URL": "",
        "MOBILITY_OVERPASS_URL": "",
        "MOBILITY_NOMINATIM_URL": "",
        "MOBILITY_TILES_ENABLED": "false",
        "MOBILITY_TILE_URL": "",
        "MOBILITY_TILE_ATTRIBUTION": "",
        "MOBILITY_ALLOWED_TILE_ORIGIN": "",
    }
    assert {name: child_env.get(name) for name in forced_off} == forced_off
    if web:
        assert child_env["MOBILITY_ENABLED"] == "true"
    assert SECRET_CANARY not in child_env.values()


def test_test_api_app_uses_closed_open_settings_without_env_file_or_provider_io(
    harness, monkeypatch, tmp_path
):
    module = _require_harness(harness)
    api_root = str(PROJECT_ROOT / "apps" / "api")
    if api_root not in sys.path:
        monkeypatch.setattr(sys, "path", [api_root, *sys.path])
    import app.mobility.router as mobility_router
    from app.mobility.providers import registry

    hostile = {
        "GOOGLE_MAPS_ENABLED": "true",
        "MOBILITY_ENABLED": "false",
        "MOBILITY_LIVE_ENABLED": "true",
        "MOBILITY_ROUTING_PROVIDER": "ors",
        "MOBILITY_PLACES_PROVIDER": "osm_overpass",
        "MOBILITY_GEOCODER_PROVIDER": "nominatim",
        "MOBILITY_ORS_API_KEY": SECRET_CANARY,
        "MOBILITY_ORS_BASE_URL": "https://unit.example.test/ors",
        "MOBILITY_OVERPASS_URL": "https://unit.example.test/overpass",
        "MOBILITY_NOMINATIM_URL": "https://unit.example.test/geocode",
        "MOBILITY_TILES_ENABLED": "true",
        "MOBILITY_TILE_URL": "https://unit.example.test/{z}/{x}/{y}.png",
        "MOBILITY_TILE_ATTRIBUTION": "unit attribution",
        "MOBILITY_ALLOWED_TILE_ORIGIN": "https://unit.example.test",
    }
    for name, value in hostile.items():
        monkeypatch.setenv(name, value)

    (tmp_path / ".env").write_text(
        "GOOGLE_MAPS_ENABLED=true\nMOBILITY_ORS_API_KEY=UNIT_SYNTHETIC_DOTENV_CANARY\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    env_file_reads = []
    original_io_open = io.open

    def guarded_io_open(file, *args, **kwargs):
        if Path(str(file)).name == ".env":
            env_file_reads.append(str(file))
            raise AssertionError("synthetic guard blocked .env reads")
        return original_io_open(file, *args, **kwargs)

    monkeypatch.setattr(io, "open", guarded_io_open)
    network_attempts = []
    import httpx

    def forbidden_http_client(*args, **kwargs):
        network_attempts.append("httpx")
        raise AssertionError("synthetic guard blocked provider traffic")

    monkeypatch.setattr(httpx, "AsyncClient", forbidden_http_client)
    monkeypatch.setattr(registry, "_load_adapter", lambda *args: pytest.fail("live adapter selected"))
    providers = {}
    original_route_factory = mobility_router.build_route_provider
    original_places_factory = mobility_router.build_places_provider

    def capture_route_provider(settings):
        providers["route_settings"] = settings
        providers["route"] = original_route_factory(settings)
        return providers["route"]

    def capture_places_provider(settings):
        providers["places_settings"] = settings
        providers["places"] = original_places_factory(settings)
        return providers["places"]

    monkeypatch.setattr(mobility_router, "build_route_provider", capture_route_provider)
    monkeypatch.setattr(mobility_router, "build_places_provider", capture_places_provider)
    module._create_test_api_app(object())

    settings = providers["route_settings"]
    assert settings is providers["places_settings"]
    assert settings.enabled is True
    assert settings.live_enabled is False
    assert settings.google_maps_enabled is False
    assert settings.routing_provider == "disabled"
    assert settings.places_provider == "disabled"
    assert settings.geocoder_provider == "disabled"
    assert settings.ors_api_key.get_secret_value() == ""
    assert settings.ors_base_url == settings.overpass_url == settings.nominatim_url == ""
    assert settings.tiles_enabled is False
    assert settings.tile_url == settings.tile_attribution == settings.allowed_tile_origin == ""
    assert settings.provider_policies == settings.expected_policy_hashes == {}
    assert type(providers["route"]).__name__ == "DisabledRouteProvider"
    assert type(providers["places"]).__name__ == "DisabledPlacesProvider"

    route_result = asyncio.run(
        providers["route"].compute_route(
            SimpleNamespace(
                request=SimpleNamespace(listing_id=100001, campus_id="khu_i", requested_mode="WALK"),
                destination=SimpleNamespace(coordinate_version="unit-v1"),
            )
        )
    )
    places_result = asyncio.run(
        providers["places"].nearby(
            SimpleNamespace(
                request=SimpleNamespace(listing_id=100001, radius_m=500, categories=["grocery"])
            )
        )
    )
    assert route_result.status == places_result.status == "NOT_CONFIGURED"
    assert env_file_reads == []
    assert network_attempts == []


def test_browser_envelope_hashes_python_canonical_json_verbatim(tmp_path):
    node = shutil.which("node")
    assert node is not None, "local Node.js is required for the offline hash-boundary guard"
    unit_rows = [
        {
            "id": 100001 + index,
            "area": 21.0 if index == 0 else None,
            "description": None,
            "title": "Cần Thơ" if index == 0 else f"Unit title {index + 1}",
        }
        for index in range(789)
    ]
    canonical = json.dumps(
        unit_rows,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    envelope = {
        "schema_version": 1,
        "operation_id": OPERATION_ID,
        "public_dto_sha256": digest,
        "canonical_public_json": canonical,
    }
    envelope_path = tmp_path / "unit-expected-public-data.json"
    envelope_path.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
    script_path = PROJECT_ROOT / "apps/web/e2e/mobility-catalog-acceptance.cjs"
    node_check = (
        "const fs=require('node:fs');"
        "const helper=require(process.argv[1]);"
        "const value=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));"
        "helper.validateExpectedEnvelope(value);"
    )
    accepted = subprocess.run(
        [node, "-e", node_check, str(script_path), str(envelope_path)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert accepted.returncode == 0, "Python canonical float/NULL/Unicode hash must be accepted"

    envelope["public_dto_sha256"] = "0" * 64
    envelope_path.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
    rejected = subprocess.run(
        [node, "-e", node_check, str(script_path), str(envelope_path)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert rejected.returncode != 0
    assert "Cần Thơ" not in rejected.stdout + rejected.stderr


def test_browser_ieee754_bits_match_literal_python_and_approved_source_vectors(tmp_path):
    special_vectors = (
        (10.0, "4024000000000000"),
        (10.1, "4024333333333333"),
        (0.0, "0000000000000000"),
        (-0.0, "0000000000000000"),
        (1.234e-6, "3eb4b3fd5942cd96"),
    )
    assert len(APPROVED_SOURCE_COORDINATE_VECTORS) == 54
    for value, expected_bits in special_vectors:
        assert _independent_binary64_hex(value) == expected_bits
    for lat, lng, expected_lat_bits, expected_lng_bits in APPROVED_SOURCE_COORDINATE_VECTORS:
        assert _independent_binary64_hex(lat) == expected_lat_bits
        assert _independent_binary64_hex(lng) == expected_lng_bits

    program = r'''
const fs = require('node:fs');
const h = require(process.argv[1]);
if (typeof h.binary64BitsHex !== 'function') throw Error('missing pure helper: binary64BitsHex');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const actual = [10, 10.1, 0, -0, 1.234e-6].map(h.binary64BitsHex);
for (const vector of payload.sourceVectors) {
  actual.push(h.binary64BitsHex(vector[0]), h.binary64BitsHex(vector[1]));
}
if (JSON.stringify(actual) !== JSON.stringify(payload.expectedBits)) throw Error('binary64 literal mismatch');
'''
    source_vectors = [list(vector[:2]) for vector in APPROVED_SOURCE_COORDINATE_VECTORS]
    expected_bits = [bits for _, bits in special_vectors]
    for _, _, lat_bits, lng_bits in APPROVED_SOURCE_COORDINATE_VECTORS:
        expected_bits.extend((lat_bits, lng_bits))
    result = _run_node_helper(
        tmp_path,
        program,
        {"sourceVectors": source_vectors, "expectedBits": expected_bits},
    )
    assert result.returncode == 0, result.stderr


def test_browser_cluster_snapshot_accepts_exact_members_and_returns_source_bound_digest(tmp_path):
    source_rows = _unit_source_rows()
    expected_rows, snapshot = _unit_cluster_case()
    expected_digest = _independent_positioned_members_sha256(source_rows)
    program = r'''
const fs = require('node:fs');
const h = require(process.argv[1]);
if (typeof h.validateClusterSnapshot !== 'function') throw Error('missing pure helper: validateClusterSnapshot');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const receipt = h.validateClusterSnapshot(payload.expectedRows, payload.snapshot);
if (!receipt || receipt.positioned_listing_count !== 787 ||
    receipt.actual_positioned_members_sha256 !== payload.expectedDigest) {
  throw Error('cluster membership receipt mismatch');
}
'''
    result = _run_node_helper(
        tmp_path,
        program,
        {
            "expectedRows": expected_rows,
            "snapshot": snapshot,
            "expectedDigest": expected_digest,
        },
    )
    assert result.returncode == 0, result.stderr


def test_browser_runner_reads_live_map_snapshot_before_selecting_listings():
    browser_path = PROJECT_ROOT / "apps/web/e2e/mobility-catalog-acceptance.cjs"
    source = browser_path.read_text(encoding="utf-8")
    assert "await verifyMountedClusterSnapshot(page, expectedRows)" in source
    runner = source.split("async function runBrowser(", 1)[1].split("\nasync function main(", 1)[0]
    snapshot_call = runner.index("await verifyMountedClusterSnapshot(page, expectedRows)")
    selection_definition = runner.index("async function selectAndRead")
    assert snapshot_call < selection_definition
    assert "const id980 = expectedRows.find((row) => row.id === 980)" in runner
    assert "validateId980Evidence(expectedRows, id980Evidence)" in runner
    assert "sourceLinkHref: await uniqueOptionalHref(sourceLink)" in runner
    assert "contactLinkHref: await uniqueOptionalHref(id980ContactLink)" in runner


def test_browser_snapshot_reader_uses_live_map_event_result_not_expected_rows(tmp_path):
    expected_rows, snapshot = _unit_cluster_case()
    expected_digest = _independent_positioned_members_sha256(_unit_source_rows())
    program = r'''
const fs = require('node:fs');
const h = require(process.argv[1]);
if (typeof h.verifyMountedClusterSnapshot !== 'function') throw Error('missing mounted-map snapshot seam');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const calls = [];
let current = payload.snapshot;
global.CustomEvent = class { constructor(type, init) { this.type = type; this.detail = init.detail; } };
const container = { dispatchEvent(event) {
  calls.push(event.type);
  event.detail.respond(current);
  return true;
} };
const page = { getByTestId(name) {
  if (name !== 'mobility-map') throw Error('wrong map container');
  return { evaluate(callback) { return callback(container); } };
} };
(async () => {
  const receipt = await h.verifyMountedClusterSnapshot(page, payload.expectedRows);
  if (JSON.stringify(calls) !== JSON.stringify(['mobility:listing-layer-snapshot'])) throw Error('live snapshot event missing');
  if (receipt.positioned_listing_count !== 787 || receipt.actual_positioned_members_sha256 !== payload.expectedDigest)
    throw Error('live snapshot result mismatch');
  current = JSON.parse(JSON.stringify(payload.snapshot));
  current.members[0].lng += 0.001;
  let rejected = false;
  try { await h.verifyMountedClusterSnapshot(page, payload.expectedRows); } catch { rejected = true; }
  if (!rejected) throw Error('wrong live layer snapshot was ignored');
})().catch((error) => { process.stderr.write(String(error)); process.exitCode = 1; });
'''
    result = _run_node_helper(
        tmp_path,
        program,
        {
            "expectedRows": expected_rows,
            "snapshot": snapshot,
            "expectedDigest": expected_digest,
        },
    )
    assert result.returncode == 0, result.stderr


def test_browser_optional_link_href_requires_zero_one_or_many_count_semantics(tmp_path):
    program = r'''
const h = require(process.argv[1]);
if (typeof h.uniqueOptionalHref !== 'function') throw Error('missing unique optional href helper');
const locator = (count, href) => ({
  count: async () => count,
  getAttribute: async (name) => name === 'href' ? href : null,
});
(async () => {
  if (await h.uniqueOptionalHref(locator(0, null)) !== null) throw Error('zero-link case mismatch');
  if (await h.uniqueOptionalHref(locator(1, 'https://unit.example.test/source')) !== 'https://unit.example.test/source')
    throw Error('one-link case mismatch');
  let rejected = false;
  try { await h.uniqueOptionalHref(locator(2, 'https://unit.example.test/source')); } catch { rejected = true; }
  if (!rejected) throw Error('multiple-link ambiguity accepted');
})().catch((error) => { process.stderr.write(String(error)); process.exitCode = 1; });
'''
    result = _run_node_helper(tmp_path, program, {})
    assert result.returncode == 0, result.stderr


def test_browser_run_uses_snapshot_before_selection_and_rejects_bypass_mutant(tmp_path):
    expected_rows = _unit_public_rows(_unit_source_rows())
    source_rows = _unit_source_rows()
    _, snapshot = _unit_cluster_case()
    receipt_path = str(tmp_path / "unit-browser-receipt.json")
    screenshot_path = str(tmp_path / "unit-browser-screenshot.png")
    program = r'''
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const helperPath = process.argv[1];
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const receiptPath = process.argv[3], screenshotPath = process.argv[4];
const source = fs.readFileSync(helperPath, 'utf8');
const marker = 'const clusterEvidence = await verifyMountedClusterSnapshot(page, expectedRows);';
if (!source.includes(marker)) throw Error('runner snapshot assignment missing');
global.CustomEvent = class { constructor(type, init) { this.type = type; this.detail = init.detail; } };

async function runWith(h, expectedError) {
  let eventObserved = false;
  let browserClosed = false;
  const listeners = {};
  const areaText = (row) => (row.area == null ? 'Diện tích chưa rõ' : `${row.area} m²`) +
    (row.district ? ` · ${row.district}` : '');
  const buttons = payload.expectedRows.map((row) => ({
    getAttribute: (name) => name === 'data-listing-id' ? String(row.id) : null,
    querySelector: (selector) => selector === 'span:nth-of-type(1)' ? { textContent: row.title } :
      selector === 'span:nth-of-type(3)' ? { textContent: areaText(row) } : null,
  }));
  const container = { dispatchEvent(event) {
    if (event.type !== 'mobility:listing-layer-snapshot') throw Error('wrong snapshot event');
    event.detail.respond(payload.snapshot);
    eventObserved = true;
    return true;
  } };
  const page = {
    setDefaultTimeout() {},
    on(name, callback) { listeners[name] = callback; },
    async goto() {
      for (let pageNumber = 1; pageNumber <= 8; pageNumber += 1) {
        listeners.response({
          url: () => `http://127.0.0.1:3032/api/mobility/listings?page=${pageNumber}&size=100`,
          status: () => 200,
        });
      }
    },
    async waitForFunction() {},
    getByRole() { return { count: async () => 1 }; },
    getByTestId(name) {
      if (name !== 'mobility-map') throw Error('wrong mounted map selector');
      return { evaluate: async (callback) => callback(container) };
    },
    locator(selector) {
      if (selector === 'button[data-listing-id]') return { evaluateAll: async (callback) => callback(buttons) };
      if (selector === 'section[aria-label="Chi tiết tin được chọn"]') return { last: () => ({}) };
      if (selector.startsWith('button[data-listing-id="')) return {
        count: async () => 1,
        click: async () => {
          if (!eventObserved) throw Error('SNAPSHOT_NOT_OBSERVED');
          throw Error('STOP_FIRST_SELECTION');
        },
      };
      throw Error('unexpected locator');
    },
  };
  const context = {
    async route() {},
    async newPage() { return page; },
    async close() {},
  };
  const browser = {
    async newContext() { return context; },
    async close() { browserClosed = true; },
  };
  const originalLoad = Module._load;
  Module._load = function(request, parent, isMain) {
    if (request === 'playwright') return { chromium: { launch: async () => browser } };
    return originalLoad.call(this, request, parent, isMain);
  };
  try {
    let caught = null;
    try {
      await h.runBrowser(payload.expectedRows, payload.envelope, receiptPath, screenshotPath);
    } catch (error) {
      caught = error;
    }
    if (!caught || caught.message !== expectedError) throw Error(`unexpected first-selection outcome: ${caught}`);
    if (!browserClosed) throw Error('browser was not closed after sentinel stop');
    if (fs.existsSync(receiptPath) || fs.existsSync(screenshotPath)) throw Error('evidence was written before completion');
    return eventObserved;
  } finally {
    Module._load = originalLoad;
  }
}

(async () => {
  const h = require(helperPath);
  if (typeof h.runBrowser !== 'function') throw Error('missing offline runBrowser seam');
  if (await runWith(h, 'STOP_FIRST_SELECTION') !== true) throw Error('live snapshot was not observed');
  const mutantSource = source.replace(marker,
    "const clusterEvidence = { positioned_listing_count: 787, actual_positioned_members_sha256: '0'.repeat(64) };");
  const mutant = new Module(helperPath + '.unit-mutant', module);
  mutant.filename = helperPath;
  mutant.paths = Module._nodeModulePaths(path.dirname(helperPath));
  mutant._compile(mutantSource, helperPath);
  if (await runWith(mutant.exports, 'SNAPSHOT_NOT_OBSERVED') !== false)
    throw Error('snapshot-bypass mutant unexpectedly observed the event');
  const earlySelectionSource = source.replace(
    marker,
    `await page.locator('button[data-listing-id="100001"]').click();
${marker}`,
  );
  const earlySelectionMutant = new Module(helperPath + '.unit-early-selection-mutant', module);
  earlySelectionMutant.filename = helperPath;
  earlySelectionMutant.paths = Module._nodeModulePaths(path.dirname(helperPath));
  earlySelectionMutant._compile(earlySelectionSource, helperPath);
  if (await runWith(earlySelectionMutant.exports, 'SNAPSHOT_NOT_OBSERVED') !== false)
    throw Error('early-selection snapshot bypass mutant unexpectedly observed the event');
})().catch((error) => { process.stderr.write(String(error)); process.exitCode = 1; });
'''
    expected_digest = _independent_positioned_members_sha256(source_rows)
    result = _run_node_helper(
        tmp_path,
        program,
        {
            "expectedRows": expected_rows,
            "snapshot": snapshot,
            "expectedDigest": expected_digest,
            "envelope": {"operation_id": OPERATION_ID},
        },
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-member",
        "extra-member",
        "duplicate-id",
        "wrong-id",
        "wrong-coordinate",
        "string-id",
        "boolean-coordinate",
        "string-coordinate",
        "extra-member-key",
        "extra-top-key",
        "array-top-level",
        "wrong-state",
        "negative-generation",
        "boolean-generation",
        "latitude-out-of-range",
    ],
)
def test_browser_cluster_snapshot_rejects_actual_membership_counterexamples(tmp_path, mutation):
    expected_rows, snapshot = _unit_cluster_case(mutation)
    program = r'''
const fs = require('node:fs');
const h = require(process.argv[1]);
if (typeof h.validateClusterSnapshot !== 'function') throw Error('missing pure helper: validateClusterSnapshot');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
let rejected = false;
try { h.validateClusterSnapshot(payload.expectedRows, payload.snapshot); } catch { rejected = true; }
if (!rejected) throw Error('cluster counterexample accepted');
'''
    result = _run_node_helper(
        tmp_path,
        program,
        {"expectedRows": expected_rows, "snapshot": snapshot},
    )
    assert result.returncode == 0, result.stderr


def test_browser_id980_withheld_evidence_is_bound_to_same_selected_source_row(tmp_path):
    rows, evidence = _id980_case()
    program = r'''
const fs = require('node:fs');
const h = require(process.argv[1]);
if (typeof h.validateId980Evidence !== 'function') throw Error('missing pure helper: validateId980Evidence');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
h.validateId980Evidence(payload.rows, payload.evidence);
'''
    result = _run_node_helper(tmp_path, program, {"rows": rows, "evidence": evidence})
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "mutation",
    [
        "alternate-withheld-row",
        "wrong-title",
        "not-selected",
        "wrong-source-link",
        "wrong-contact-link",
        "missing-partial-label",
        "wrong-fallback-description",
        "unsafe-source-url",
        "wrong-withheld-state",
        "nonempty-withheld-description",
        "duplicate-id980",
        "unsafe-contact-url",
        "contact-link-present-when-unsafe",
    ],
)
def test_browser_id980_rejects_wrong_row_or_cross_row_evidence(tmp_path, mutation):
    rows, evidence = _id980_case(mutation)
    program = r'''
const fs = require('node:fs');
const h = require(process.argv[1]);
if (typeof h.validateId980Evidence !== 'function') throw Error('missing pure helper: validateId980Evidence');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
let rejected = false;
try { h.validateId980Evidence(payload.rows, payload.evidence); } catch { rejected = true; }
if (!rejected) throw Error('ID 980 counterexample accepted');
'''
    result = _run_node_helper(tmp_path, program, {"rows": rows, "evidence": evidence})
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("contact_url", [None, "javascript:alert(1)"])
def test_browser_id980_omits_missing_or_unsafe_contact_link(tmp_path, contact_url):
    rows, evidence = _id980_case()
    rows[0]["source_contact_url"] = contact_url
    evidence["contactLinkHref"] = None
    program = r'''
const fs = require('node:fs');
const h = require(process.argv[1]);
if (typeof h.validateId980Evidence !== 'function') throw Error('missing pure helper: validateId980Evidence');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
h.validateId980Evidence(payload.rows, payload.evidence);
'''
    result = _run_node_helper(tmp_path, program, {"rows": rows, "evidence": evidence})
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-pin",
        "extra-pin",
        "false-ac",
        "bool-count",
        "metadata-count",
        "core-table-count",
        "readonly-bool-is-int",
        "unknown-status",
        "mock-evidence",
        "missing-browser-digest",
        "changed-browser-digest",
        "operation-mismatch",
        "wrong-source-membership",
        "before-after-table-mismatch",
        "before-after-view-mismatch",
        "missing-table-in-both-digests",
        "browser-operation-mismatch",
        "browser-data-hash-mismatch",
        "browser-external-attempt",
    ],
)
def test_real_receipt_rejects_incomplete_or_counterexample_evidence(harness, mutation):
    module = _require_harness(harness)
    source_rows = _unit_source_rows()
    code_pins = _unit_code_pins()
    receipt, operation = _unit_receipt(source_rows, code_pins)
    module.validate_real_receipt_document(receipt, source_rows, code_pins, operation)
    receipt = copy.deepcopy(receipt)

    if mutation == "missing-pin":
        receipt["code_sha256"].pop(CODE_PIN_PATHS[0])
    elif mutation == "extra-pin":
        receipt["code_sha256"]["unexpected.py"] = "3" * 64
    elif mutation == "false-ac":
        receipt["checks"]["AC4"] = False
    elif mutation == "bool-count":
        receipt["counts"]["http"]["rows"] = True
    elif mutation == "metadata-count":
        receipt["table_digests_before"]["public.catalog_handoff_metadata"]["row_count"] = 788
        receipt["table_digests_after"]["public.catalog_handoff_metadata"]["row_count"] = 788
    elif mutation == "core-table-count":
        receipt["table_digests_before"]["public.aggregated_listings"]["row_count"] = 801
        receipt["table_digests_after"]["public.aggregated_listings"]["row_count"] = 801
    elif mutation == "readonly-bool-is-int":
        receipt["readonly_probe"]["transaction_read_only"] = 1
    elif mutation == "unknown-status":
        receipt["status"] = "PREPARATION_ONLY"
    elif mutation == "mock-evidence":
        receipt["evidence_kind"] = "SYNTHETIC_FIXTURE"
    elif mutation == "missing-browser-digest":
        receipt.pop("browser_receipt_sha256")
    elif mutation == "changed-browser-digest":
        receipt["browser_receipt_sha256"] = "0" * 64
    elif mutation == "operation-mismatch":
        receipt["target"]["port"] = 5432
    elif mutation == "wrong-source-membership":
        receipt["actual_ids_sha256"] = "0" * 64
    elif mutation == "before-after-table-mismatch":
        receipt["table_digests_after"]["public.users"]["sha256"] = "4" * 64
    elif mutation == "before-after-view-mismatch":
        receipt["view_digest_after"] = "5" * 64
    elif mutation == "missing-table-in-both-digests":
        receipt["table_digests_before"].pop("public.users")
        receipt["table_digests_after"].pop("public.users")
    elif mutation == "browser-operation-mismatch":
        receipt["browser"]["operation_id"] = "00000000-0000-4000-8000-000000000001"
        receipt["browser_receipt_sha256"] = _independent_json_sha256(receipt["browser"])
    elif mutation == "browser-data-hash-mismatch":
        receipt["browser"]["expected_public_data_sha256"] = "6" * 64
        receipt["browser_receipt_sha256"] = _independent_json_sha256(receipt["browser"])
    else:
        receipt["browser"]["external_attempts"] = 1
        receipt["browser_receipt_sha256"] = _independent_json_sha256(receipt["browser"])

    with pytest.raises(ValueError):
        module.validate_real_receipt_document(
            receipt,
            expected_source_rows=source_rows,
            expected_code_pin_hashes=code_pins,
            expected_operation=operation,
        )


def test_verify_without_runtime_config_fails_with_one_redacted_json_line(tmp_path):
    result = subprocess.run(
        [sys.executable, str(HARNESS_PATH), "verify", "--runtime-dir", str(tmp_path)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    _assert_generic_cli_failure(result)


def test_verify_receipt_without_real_acceptance_fails_closed(tmp_path):
    result = subprocess.run(
        [sys.executable, str(HARNESS_PATH), "verify-receipt", "--runtime-dir", str(tmp_path)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    _assert_generic_cli_failure(result)


def test_invalid_config_rejection_error_redacts_secret_canary(harness):
    module = _require_harness(harness)
    raw = dict(TARGET)
    raw["port"] = 5432

    with pytest.raises(ValueError, match=r"^Invalid acceptance configuration\.$") as error:
        module.validate_runtime_config(raw)

    assert SECRET_CANARY not in str(error.value)


def test_wrong_port_cli_failure_is_generic_and_cannot_reach_any_engine_or_socket(tmp_path):
    runtime_dir = tmp_path / "unit-runtime"
    runtime_dir.mkdir()
    config_path = runtime_dir / RUNTIME_CONFIG_NAME
    raw = dict(TARGET)
    raw["port"] = 5432
    config_path.write_text(json.dumps(raw), encoding="utf-8")

    factory_marker = tmp_path / "engine-factory-called"
    socket_marker = tmp_path / "socket-connect-called"
    bootstrap = "\n".join(
        (
            "import pathlib, importlib.util, socket, sqlalchemy, sqlalchemy.engine, sys",
            f"script = {json.dumps(str(HARNESS_PATH))}",
            f"runtime_dir = {json.dumps(str(runtime_dir))}",
            f"factory_marker = {json.dumps(str(factory_marker))}",
            f"socket_marker = {json.dumps(str(socket_marker))}",
            "def forbidden_engine(*args, **kwargs):",
            "    pathlib.Path(factory_marker).write_text('called', encoding='utf-8')",
            "    raise RuntimeError('unit engine guard')",
            "def forbidden_socket(*args, **kwargs):",
            "    pathlib.Path(socket_marker).write_text('called', encoding='utf-8')",
            "    raise RuntimeError('unit socket guard')",
            "sqlalchemy.create_engine = forbidden_engine",
            "sqlalchemy.engine.create_engine = forbidden_engine",
            "socket.socket.connect = forbidden_socket",
            "socket.socket.connect_ex = forbidden_socket",
            "spec = importlib.util.spec_from_file_location('unit_cli_bootstrap',script)",
            "module = importlib.util.module_from_spec(spec)",
            "sys.modules[spec.name] = module",
            "spec.loader.exec_module(module)",
            "module._verify_catalog_phase_gate = lambda: None",
            "module._runtime_directory = lambda path: pathlib.Path(path)",
            "original_load = module._load_runtime_config",
            "def observed_load(path):",
            "    pathlib.Path(runtime_dir,'config-read-called').write_text('called',encoding='utf-8')",
            "    return original_load(path)",
            "module._load_runtime_config = observed_load",
            "sys.exit(module.main(['verify','--runtime-dir',runtime_dir]))",
        )
    )

    result = subprocess.run(
        [sys.executable, "-c", bootstrap],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    _assert_generic_cli_failure(result)
    assert SECRET_CANARY not in result.stdout
    assert SECRET_CANARY not in result.stderr
    assert not factory_marker.exists()
    assert not socket_marker.exists()
    assert (runtime_dir / 'config-read-called').exists()


@pytest.mark.parametrize('arguments', [[], ['verify'], ['verify', '--runtime-dir', 'D:/tmp', SECRET_CANARY]])
def test_remediation_cli_parser_never_echoes_arguments(arguments):
    result = subprocess.run([sys.executable, str(HARNESS_PATH), *arguments], capture_output=True,
                            text=True, timeout=5, cwd=PROJECT_ROOT)
    _assert_generic_cli_failure(result)
    assert SECRET_CANARY not in result.stdout + result.stderr


@pytest.mark.parametrize('field,value', [('description_is_partial', 1), ('unit_type_uncertain', 0),
                                        ('price', 1000000.0), ('area', 21)])
def test_remediation_projection_rejects_json_type_changes(harness, field, value):
    source = _unit_source_rows()
    source[0]['area'] = 21.0
    actual = _unit_public_rows(source)
    actual[0][field] = value
    with pytest.raises(ValueError):
        harness.validate_catalog_projection(source, actual)


@pytest.mark.parametrize('location', ['top', 'browser', 'table', 'view', 'http'])
def test_remediation_receipt_rejects_extra_secret_keys(harness, location):
    source = _unit_source_rows()
    pins = _unit_code_pins()
    receipt, operation = _unit_receipt(source, pins)
    destination = {'top': receipt, 'browser': receipt['browser'],
                   'table': receipt['table_digests_before']['public.users'],
                   'view': receipt['view_digest_before'], 'http': receipt['counts']['http']}[location]
    destination['password'] = SECRET_CANARY
    receipt['table_digests_after'] = copy.deepcopy(receipt['table_digests_before'])
    receipt['view_digest_after'] = copy.deepcopy(receipt['view_digest_before'])
    receipt['browser_receipt_sha256'] = _independent_json_sha256(receipt['browser'])
    with pytest.raises(ValueError):
        harness.validate_real_receipt_document(receipt, source, pins, operation)


def _unit_clone_metadata():
    labels = {'nckh.acceptance.operation': OPERATION_ID,
              'nckh.acceptance.catalog_sha256': PINNED_CATALOG_SHA256,
              'com.docker.compose.project': TARGET['project']}
    ports = {'5432/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '5455'}]}
    container = {'Name': '/' + TARGET['container'],
                 'Image': 'sha256:dcea513d8f8c0bd2b314bfaa672d1bb3a91d100c401afe34f139dcd3c5869bdd',
                 'Config': {'Labels': labels}, 'State': {'Running': True, 'Health': {'Status': 'healthy'}},
                 'HostConfig': {'PortBindings': ports}, 'NetworkSettings': {'Ports': ports},
                 'Mounts': [{'Type': 'volume', 'Name': TARGET['volume'],
                             'Destination': '/var/lib/postgresql/data', 'RW': True}]}
    volume = {'Name': TARGET['volume'], 'Labels': copy.deepcopy(labels), 'Driver': 'local'}
    return container, volume


@pytest.mark.parametrize('mutation', ['none', 'image', 'operation', 'volume', 'port', 'project', 'mount'])
def test_remediation_clone_identity_is_observed(harness, mutation):
    validator = getattr(harness, 'validate_clone_metadata', None)
    assert callable(validator), 'missing observed Docker metadata guard'
    container, volume = _unit_clone_metadata()
    if mutation == 'image': container['Image'] = 'sha256:' + '0' * 64
    if mutation == 'operation': container['Config']['Labels']['nckh.acceptance.operation'] = 'wrong'
    if mutation == 'volume': volume['Name'] = 'nckh_pgdata'
    if mutation == 'port': container['NetworkSettings']['Ports']['5432/tcp'][0]['HostIp'] = '0.0.0.0'
    if mutation == 'project': volume['Labels']['com.docker.compose.project'] = 'nckh'
    if mutation == 'mount': container['Mounts'][0]['Destination'] = '/wrong'
    if mutation == 'none':
        observed = validator(container, volume, harness.validate_runtime_config(dict(TARGET)))
        assert observed['target']['port'] == 5455
        assert observed['image_id'] == container['Image']
    else:
        with pytest.raises(ValueError): validator(container, volume, harness.validate_runtime_config(dict(TARGET)))


def _unit_privileges():
    return {'database_name': TARGET['database'], 'role_name': TARGET['user'], 'server_port': 5432,
            'read_only': 'on', 'default_read_only': 'on', 'superuser': False, 'createdb': False,
            'createrole': False, 'bypassrls': False, 'database_create': False, 'schema_create': False,
            'dangerous_membership': False, 'all_select': True, 'any_write': False}


@pytest.mark.parametrize('field,value', [('server_port', 5455), ('superuser', True), ('createdb', True),
    ('createrole', True), ('bypassrls', True), ('database_create', True), ('schema_create', True),
    ('dangerous_membership', True), ('any_write', True), ('all_select', False), ('default_read_only', 'off')])
def test_remediation_reader_proof_rejects_effective_write_privileges(harness, field, value):
    validator = getattr(harness, 'validate_reader_privileges', None)
    assert callable(validator), 'missing effective readonly role guard'
    snapshot = _unit_privileges()
    validator(snapshot)
    snapshot[field] = value
    with pytest.raises(ValueError): validator(snapshot)


def test_remediation_runtime_requires_exact_path_before_acl(harness, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(harness, '_runtime_acl_snapshot', lambda path: calls.append(path), raising=False)
    with pytest.raises(ValueError): harness._runtime_directory(tmp_path)
    assert calls == []


@pytest.mark.parametrize('mutation', ['none', 'owner', 'inherited', 'other-user'])
def test_remediation_runtime_acl_is_single_user_and_protected(harness, mutation):
    validator = getattr(harness, 'validate_runtime_acl', None)
    assert callable(validator), 'missing runtime ACL guard'
    snapshot = {'current_sid': 'S-1-5-21-UNIT', 'owner_sid': 'S-1-5-21-UNIT', 'protected': True,
                'rules': [{'sid': 'S-1-5-21-UNIT', 'allow': True, 'inherited': False, 'rights': 2032127}]}
    if mutation == 'owner': snapshot['owner_sid'] = 'S-1-5-32-544'
    if mutation == 'inherited': snapshot['protected'] = False
    if mutation == 'other-user': snapshot['rules'].append({'sid': 'S-1-1-0', 'allow': True,
                                                        'inherited': False, 'rights': 2032127})
    if mutation == 'none': validator(snapshot)
    else:
        with pytest.raises(ValueError): validator(snapshot)


def test_remediation_browser_oracles_use_withheld_state_and_each_card():
    helper = PROJECT_ROOT / 'apps/web/e2e/mobility-catalog-acceptance.cjs'
    program = r'''
const h = require(process.argv[1]);
if (typeof h.validateRenderedCards !== 'function' || typeof h.validateDescriptionEvidence !== 'function')
  throw Error('missing browser behavioral oracles');
const rows = Array.from({length:789}, (_,i) => ({id:803+i,title:'Tin '+i,area:i%2?null:21,district:'Quận'}));
const cards = rows.map(r => ({id:r.id,title:r.title,area:(r.area===null?'Diện tích chưa rõ':r.area+' m²')+' · Quận'}));
h.validateRenderedCards(rows,cards);
function mustReject(fn) { let rejected=false; try {fn();} catch {rejected=true;} if(!rejected) throw Error('false green'); }
cards[700].area='999 m² · Quận'; mustReject(()=>h.validateRenderedCards(rows,cards));
cards[700].area='21 m² · Quận'; cards[700].title+=' unexpected'; mustReject(()=>h.validateRenderedCards(rows,cards));
const withheld={id:980,description:'',description_state:'WITHHELD_UNSAFE_CONTACT',description_completeness:'UNKNOWN',description_is_partial:true};
h.validateDescriptionEvidence(withheld,{detailText:'Mô tả chưa đầy đủ',paragraphs:['Tin đăng chưa có mô tả.']},true);
mustReject(()=>h.validateDescriptionEvidence(withheld,{detailText:'Mức độ mô tả chưa rõ',paragraphs:['Tin đăng chưa có mô tả.']},true));
'''
    result = subprocess.run(['node', '-e', program, str(helper)], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr


def test_remediation_serve_api_observes_clone_before_engine(harness, monkeypatch, tmp_path):
    (tmp_path / RUNTIME_CONFIG_NAME).write_text(json.dumps(TARGET), encoding='utf-8')
    calls = []
    def reject(config):
        calls.append('inspect')
        raise ValueError('wrong clone')
    def forbidden(config):
        calls.append('engine')
        raise ValueError('engine must not be reached')
    monkeypatch.setattr(harness, '_verify_catalog_phase_gate', lambda: None)
    monkeypatch.setattr(harness, '_runtime_directory', lambda path: Path(path))
    monkeypatch.setattr(harness, '_inspect_clone_identity', reject)
    monkeypatch.setattr(harness, 'connect_readonly', forbidden)
    with pytest.raises(ValueError): harness._serve_api(tmp_path)
    assert calls == ['inspect']


def test_remediation_inspect_uses_only_named_readonly_commands(harness, monkeypatch):
    container, volume = _unit_clone_metadata()
    calls = []
    def runner(argv, **kwargs):
        calls.append(argv)
        assert kwargs['timeout'] == 10 and kwargs['capture_output'] is True
        data = container if argv[1] == 'container' else volume
        return subprocess.CompletedProcess(argv, 0, json.dumps([data]), '')
    monkeypatch.setattr(harness.subprocess, 'run', runner)
    assert harness._inspect_clone_identity(harness.validate_runtime_config(TARGET))['image_id'] == container['Image']
    assert calls == [['docker', 'container', 'inspect', TARGET['container']],
                     ['docker', 'volume', 'inspect', TARGET['volume']]]


def test_remediation_actual_runtime_acl_path_guard(harness, monkeypatch, tmp_path):
    monkeypatch.setattr(harness, 'APPROVED_RUNTIME_DIR', tmp_path)
    good = {'current_sid': 'unit', 'owner_sid': 'unit', 'protected': True,
            'rules': [{'sid': 'unit', 'allow': True, 'inherited': False, 'rights': 2032127}]}
    monkeypatch.setattr(harness, '_runtime_acl_snapshot', lambda path: good)
    assert harness._runtime_directory(tmp_path) == tmp_path
    good['protected'] = False
    with pytest.raises(ValueError): harness._runtime_directory(tmp_path)


def test_remediation_db_identity_consumes_privilege_proof(harness):
    class Connection:
        def __init__(self): self.snapshot = _unit_privileges()
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def exec_driver_sql(self, sql): pass
        def execute(self, sql):
            # Ensure the real emitted SQL asks for effective grants, not only forced readonly mode.
            statement = str(sql)
            assert 'inet_server_port()' in statement and 'has_table_privilege' in statement
            assert 'pg_has_role' in statement and 'default_transaction_read_only' in statement
            return _FakeResult(mapping=self.snapshot)
    connection = Connection()
    engine = _FakeDmlEngine(connection)
    assert harness._db_connection_identity(engine) == {'database': TARGET['database'], 'role': TARGET['user']}
    connection.snapshot['any_write'] = True
    with pytest.raises(ValueError): harness._db_connection_identity(engine)


def test_remediation_native_acl_snapshot_is_parseable_without_modifying_acl(harness, tmp_path):
    snapshot = harness._runtime_acl_snapshot(tmp_path)
    assert set(snapshot) == {'current_sid','owner_sid','protected','rules'}
    assert isinstance(snapshot['rules'], list)
