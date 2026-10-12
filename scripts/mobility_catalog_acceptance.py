"""Offline-guarded runner for the separately approved catalog789 acceptance.

This module does not start infrastructure on import. The real verification
command is intentionally fail-closed and writes REAL_ACCEPTANCE.json only after
database, HTTP, browser, source-pin, and before/after checks all succeed.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
import hashlib
import httpx
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import struct
import subprocess
import sys
import time
from typing import Any
import uuid
import zipfile

from sqlalchemy import URL, create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PACKAGE_DIR = Path("D:/Dev/Data/NCKH/student-housing-docker-20261002-04")
SOURCE_CATALOG_PATH = SOURCE_PACKAGE_DIR / "catalog" / "CATALOG.jsonl"
SOURCE_ZIP_PATH = Path("D:/Dev/Data/NCKH/student-housing-789-Docker-INTERNAL.zip")
SOURCE_CATALOG_SHA256 = "b859bab1dc66808adc897f8f2b0b858d6aa2aa3954e52fc92c8e816e533b5947"
SOURCE_ZIP_SHA256 = "25cbfca2a36adf2f93772a5e48db8f6a0a8b48e777de41668d7a4b4ee5911a4a"
EXPECTED_IMAGE_ID = "sha256:dcea513d8f8c0bd2b314bfaa672d1bb3a91d100c401afe34f139dcd3c5869bdd"
PINNED_PACKAGE_ID = "ccd4bb988a93e6b676d2baa49de70d7e20a9b63c64a836bd673e514c95371d35"
SOURCE_BASELINE_TABLES = frozenset(
    {
        "_bootstrap",
        "aggregated_listings",
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
    }
)
TARGET_CONTAINER = "nckh-mobility-acceptance-db"
TARGET_PROJECT = "nckh-mobility-acceptance"
TARGET_VOLUME = "nckh_mobility_acceptance_pgdata"
TARGET_HOST = "127.0.0.1"
TARGET_PORT = 5455
TARGET_DATABASE = "mobility_catalog_acceptance"
TARGET_ROLE = "mobility_catalog_reader"
APPROVED_RUNTIME_DIR = Path("D:/Dev/Data/NCKH/mobility-catalog-acceptance-20261004-01")
API_HOST = "127.0.0.1"
API_PORT = 8032
UI_HOST = "127.0.0.1"
UI_PORT = 3032
RUNTIME_CONFIG_NAME = "runtime-config.json"
REAL_ACCEPTANCE_NAME = "REAL_ACCEPTANCE.json"
BROWSER_RECEIPT_NAME = "browser-receipt.json"
SCREENSHOT_NAME = "catalog-acceptance.png"
EXPECTED_PUBLIC_DATA_NAME = "expected-public-data.json"
ACCEPTANCE_STATUS = "REAL_CATALOG_POSTGRES_UI_VERIFIED"
ACCEPTANCE_EVIDENCE = "REAL_POSTGRES_REAL_CATALOG"
FAILURE_LINE = '{"status":"FAIL","code":"ACCEPTANCE_NOT_VERIFIED"}'
CATALOG_PHASE_GATE_SHA256 = "e08c0ee7478127d6e7d514215b32f2a7463825ec25fb246ee35f2b0ee5eff3fc"

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
SOURCE_REQUIRED_FIELDS = frozenset({"id", "title", "source", "source_id"})
PUBLIC_ARTIFACTS = (
    "docs/specs/open-mobility-migration.md",
    "docs/planning/2026-10-05-open-mobility-agent-plan.md",
    ".codex-gate.json",
)
CODE_PIN_ROOTS = (
    "apps/api/app/mobility",
    "apps/web/src/app/map",
    "apps/web/src/app/api/mobility",
    "apps/web/src/components/mobility",
)
CODE_PIN_FILES = (
    "docs/planning/open-mobility-provider-policy.md",
    "scripts/open_mobility_pilot.py",
    "scripts/open_mobility_tile_pilot.cjs",
    "apps/api/tests/test_open_mobility_pilot_guard.py",
    "apps/api/tests/test_open_mobility_tile_pilot_guard.py",
    "apps/api/tests/test_mobility_runtime_policy.py",
    "apps/api/tests/test_mobility_catalog_acceptance_guard.py",
    "apps/web/e2e/mobility-catalog-acceptance.cjs",
    "apps/web/src/lib/config.ts",
    "apps/web/src/lib/mobility-api.ts",
    "apps/web/src/lib/mobility-contracts.ts",
    "apps/api/requirements.txt",
    "apps/web/package.json",
    "apps/web/package-lock.json",
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
    "apps/web/src/lib/map-ui.ts",
    "apps/web/src/types/leaflet-markercluster.d.ts",
    "apps/web/e2e/map-ui-primitives.spec.ts",
    "apps/web/e2e/mobility-map-reuse.spec.ts",
    "docs/specs/open-mobility-map-reuse.md",
    "docs/planning/2026-10-05-open-mobility-map-reuse-plan.md",
)


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    operation_id: str
    host: str
    port: int
    database: str
    user: str
    password: str = field(repr=False)
    container: str
    project: str
    volume: str


def _runtime_mapping(raw: object) -> dict[str, object]:
    if type(raw) is RuntimeConfig:
        return {item.name: getattr(raw, item.name) for item in fields(RuntimeConfig)}
    if type(raw) is dict:
        return raw
    raise ValueError("Invalid acceptance configuration.")


def validate_runtime_config(raw: dict[str, object] | RuntimeConfig) -> RuntimeConfig:
    """Validate the exact private runtime target before any engine is created."""
    try:
        values = _runtime_mapping(raw)
        if set(values) != {item.name for item in fields(RuntimeConfig)}:
            raise ValueError
        operation_id = values["operation_id"]
        if type(operation_id) is not str or str(uuid.UUID(operation_id)) != operation_id:
            raise ValueError
        expected = {
            "host": TARGET_HOST,
            "port": TARGET_PORT,
            "database": TARGET_DATABASE,
            "user": TARGET_ROLE,
            "container": TARGET_CONTAINER,
            "project": TARGET_PROJECT,
            "volume": TARGET_VOLUME,
        }
        for name, expected_value in expected.items():
            value = values[name]
            if type(value) is not type(expected_value) or value != expected_value:
                raise ValueError
        password = values["password"]
        if type(password) is not str or not password:
            raise ValueError
        return RuntimeConfig(
            operation_id=operation_id,
            host=TARGET_HOST,
            port=TARGET_PORT,
            database=TARGET_DATABASE,
            user=TARGET_ROLE,
            password=password,
            container=TARGET_CONTAINER,
            project=TARGET_PROJECT,
            volume=TARGET_VOLUME,
        )
    except Exception:
        raise ValueError("Invalid acceptance configuration.") from None


def connect_readonly(
    config: RuntimeConfig | dict[str, object],
    *,
    engine_factory=create_engine,
):
    """Construct an engine only after revalidating the complete fixed target."""
    checked = validate_runtime_config(config)
    url = URL.create(
        "postgresql+psycopg",
        username=checked.user,
        password=checked.password,
        host=checked.host,
        port=checked.port,
        database=checked.database,
    )
    return engine_factory(
        url,
        connect_args={
            "connect_timeout": 2,
            "options": "-c statement_timeout=5000 -c lock_timeout=2000",
        },
        isolation_level="REPEATABLE READ",
        execution_options={"postgresql_readonly": True},
    )


def canonical_records_sha256(records: list[str]) -> str:
    if type(records) is not list or any(type(record) is not str for record in records):
        raise ValueError("Invalid digest records.")
    encoded = sorted(record.encode("utf-8") for record in records)
    digest = hashlib.sha256()
    for raw in encoded:
        digest.update(str(len(raw)).encode("ascii"))
        digest.update(b":")
        digest.update(raw)
        digest.update(b"\n")
    return digest.hexdigest()


def canonical_json_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _source_public_row(row: dict[str, object]) -> dict[str, object]:
    if type(row) is not dict or not SOURCE_REQUIRED_FIELDS.issubset(row):
        raise ValueError("Catalog acceptance mismatch.")
    result = {name: row.get(name) for name in PUBLIC_FIELDS if name != "position"}
    if type(result["id"]) is not int or result["id"] <= 0:
        raise ValueError("Catalog acceptance mismatch.")
    for name in ("title", "source", "source_id"):
        if type(result[name]) is not str:
            raise ValueError("Catalog acceptance mismatch.")
    if result["price"] is not None:
        if type(result["price"]) not in (int, float) or isinstance(result["price"], bool):
            raise ValueError("Catalog acceptance mismatch.")
        result["price"] = int(result["price"])
    if result["area"] is not None:
        if type(result["area"]) not in (int, float) or isinstance(result["area"], bool):
            raise ValueError("Catalog acceptance mismatch.")
        result["area"] = float(result["area"])
    images = row.get("images")
    if images is None:
        result["images"] = []
    elif type(images) is list and all(type(item) is str for item in images):
        result["images"] = list(images)
    else:
        raise ValueError("Catalog acceptance mismatch.")
    latitude = row.get("latitude")
    longitude = row.get("longitude")
    if (latitude is None) != (longitude is None):
        raise ValueError("Catalog acceptance mismatch.")
    if latitude is None:
        result["position"] = None
    else:
        if (
            type(latitude) not in (int, float)
            or isinstance(latitude, bool)
            or type(longitude) not in (int, float)
            or isinstance(longitude, bool)
        ):
            raise ValueError("Catalog acceptance mismatch.")
        result["position"] = {
            "lat": float(latitude),
            "lng": float(longitude),
            "precision": "UNKNOWN",
            "source": None,
            "verified_at": None,
        }
    return result


def _projection_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    type_counts = {"room": 0, "mini_house": 0, "studio": 0, "unknown": 0}
    area_values = 0
    positioned = 0
    for row in rows:
        raw_type = row.get("housing_type")
        kind = raw_type.strip().lower() if type(raw_type) is str else "unknown"
        if kind not in type_counts:
            kind = "unknown"
        type_counts[kind] += 1
        area_values += row.get("area") is not None
        positioned += row.get("position") is not None
    return {
        "catalog_count": len(rows),
        "housing_type_counts": type_counts,
        "area_value_count": area_values,
        "area_null_count": len(rows) - area_values,
        "position_count": positioned,
        "position_null_count": len(rows) - positioned,
    }


def validate_catalog_projection(
    source_rows: list[dict[str, object]],
    actual_rows: list[dict[str, object]],
) -> dict[str, object]:
    """Compare API DTOs to a source-derived oracle and fixed 789-row profile."""
    try:
        if type(source_rows) is not list or type(actual_rows) is not list:
            raise ValueError
        if len(source_rows) != 789 or len(actual_rows) != 789:
            raise ValueError
        source_ids = [row.get("id") if type(row) is dict else None for row in source_rows]
        if any(type(item) is not int or item <= 0 for item in source_ids):
            raise ValueError
        if len(set(source_ids)) != 789:
            raise ValueError
        expected = [_source_public_row(row) for row in source_rows]
        expected.sort(key=lambda item: item["id"])
        if _projection_metrics(expected) != {
            "catalog_count": 789,
            "housing_type_counts": {
                "room": 614,
                "mini_house": 168,
                "studio": 3,
                "unknown": 4,
            },
            "area_value_count": 153,
            "area_null_count": 636,
            "position_count": 787,
            "position_null_count": 2,
        }:
            raise ValueError
        for expected_row, actual_row in zip(expected, actual_rows, strict=True):
            if type(actual_row) is not dict or set(actual_row) != set(PUBLIC_FIELDS):
                raise ValueError
            if _canonical_json_text(actual_row) != _canonical_json_text(expected_row):
                raise ValueError
        return _projection_metrics(expected)
    except Exception:
        raise ValueError("Catalog acceptance mismatch.") from None


def _is_sha256(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _require_sha256(value: object) -> None:
    if not _is_sha256(value):
        raise ValueError


def _strict_int(value: object, expected: int | None = None) -> bool:
    return type(value) is int and (expected is None or value == expected)


def _binary64_hex(value: object) -> str:
    if type(value) not in (int, float):
        raise ValueError("Catalog acceptance mismatch.")
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError):
        raise ValueError("Catalog acceptance mismatch.") from None
    if not math.isfinite(number):
        raise ValueError("Catalog acceptance mismatch.")
    if number == 0.0:
        number = 0.0
    return struct.pack(">d", number).hex()


def _positioned_member_triples(source_rows: list[dict[str, object]]) -> list[list[object]]:
    triples: list[list[object]] = []
    for row in source_rows:
        if type(row) is not dict:
            raise ValueError("Catalog acceptance mismatch.")
        latitude = row.get("latitude")
        longitude = row.get("longitude")
        if latitude is None and longitude is None:
            continue
        if latitude is None or longitude is None:
            raise ValueError("Catalog acceptance mismatch.")
        lat_number = float(latitude) if type(latitude) in (int, float) else math.nan
        lng_number = float(longitude) if type(longitude) in (int, float) else math.nan
        if (
            not math.isfinite(lat_number)
            or not math.isfinite(lng_number)
            or not -90 <= lat_number <= 90
            or not -180 <= lng_number <= 180
        ):
            raise ValueError("Catalog acceptance mismatch.")
        row_id = row.get("id")
        if type(row_id) is not int or row_id <= 0:
            raise ValueError("Catalog acceptance mismatch.")
        triples.append([row_id, _binary64_hex(latitude), _binary64_hex(longitude)])
    if len(triples) != 787:
        raise ValueError("Catalog acceptance mismatch.")
    triples.sort(key=lambda item: item[0])
    return triples


def _target_from_operation(operation: dict[str, object]) -> dict[str, object]:
    return {
        "container": operation["container"],
        "project": operation["project"],
        "volume": operation["volume"],
        "host": operation["host"],
        "port": operation["port"],
        "database": operation["database"],
        "role": operation["role"],
    }


def validate_real_receipt_document(
    receipt: dict[str, object],
    expected_source_rows: list[dict[str, object]],
    expected_code_pin_hashes: dict[str, str],
    expected_operation: dict[str, object],
) -> None:
    """Pure receipt/schema guard; filesystem hashes are checked by its wrapper."""
    try:
        if type(receipt) is not dict or type(expected_operation) is not dict:
            raise ValueError
        _require_exact_keys(receipt, {
            'schema_version', 'operation_id', 'status', 'evidence_kind', 'completed_at', 'target',
            'image_id', 'source_catalog_sha256', 'source_zip_sha256', 'code_sha256', 'spec_sha256',
            'plan_sha256', 'gate_sha256', 'runtime_config_sha256', 'source_catalog_count',
            'actual_ids_sha256', 'public_dto_sha256', 'public_table_manifest', 'table_digests_before',
            'table_digests_after', 'view_digest_before', 'view_digest_after', 'checks', 'readonly_probe',
            'counts', 'browser', 'browser_receipt_sha256', 'screenshot_sha256', 'external_attempts',
        })
        if receipt.get("schema_version") != 1 or type(receipt.get("schema_version")) is not int:
            raise ValueError
        if receipt.get("status") != ACCEPTANCE_STATUS:
            raise ValueError
        if receipt.get("evidence_kind") != ACCEPTANCE_EVIDENCE:
            raise ValueError
        operation_id = expected_operation.get("operation_id")
        if receipt.get("operation_id") != operation_id:
            raise ValueError
        if receipt.get("target") != _target_from_operation(expected_operation):
            raise ValueError
        if receipt.get("image_id") != EXPECTED_IMAGE_ID:
            raise ValueError
        if receipt.get("source_catalog_sha256") != SOURCE_CATALOG_SHA256:
            raise ValueError
        if receipt.get("source_zip_sha256") != SOURCE_ZIP_SHA256:
            raise ValueError
        if not _strict_int(receipt.get("source_catalog_count"), 789):
            raise ValueError
        completed_at = receipt.get("completed_at")
        if type(completed_at) is not str or not completed_at.endswith("Z"):
            raise ValueError
        datetime.fromisoformat(completed_at[:-1] + "+00:00")

        ids = [row.get("id") if type(row) is dict else None for row in expected_source_rows]
        if (
            len(ids) != 789
            or any(type(item) is not int or item <= 0 for item in ids)
            or len(set(ids)) != 789
        ):
            raise ValueError
        expected_ids_hash = canonical_json_sha256(sorted(ids))
        expected_rows = [_source_public_row(row) for row in expected_source_rows]
        expected_rows.sort(key=lambda item: item["id"])
        expected_metrics = {
            "catalog_count": 789,
            "housing_type_counts": {
                "room": 614,
                "mini_house": 168,
                "studio": 3,
                "unknown": 4,
            },
            "area_value_count": 153,
            "area_null_count": 636,
            "position_count": 787,
            "position_null_count": 2,
        }
        if _projection_metrics(expected_rows) != expected_metrics:
            raise ValueError
        expected_positioned_members_sha256 = canonical_json_sha256(
            _positioned_member_triples(expected_source_rows)
        )
        if receipt.get("actual_ids_sha256") != expected_ids_hash:
            raise ValueError
        expected_public_hash = canonical_json_sha256(expected_rows)
        if receipt.get("public_dto_sha256") != expected_public_hash:
            raise ValueError

        code_digests = receipt.get("code_sha256")
        if type(code_digests) is not dict or code_digests != expected_code_pin_hashes:
            raise ValueError
        if not code_digests or any(not _is_sha256(value) for value in code_digests.values()):
            raise ValueError
        for name in ("spec_sha256", "plan_sha256", "gate_sha256", "runtime_config_sha256"):
            _require_sha256(receipt.get(name))

        expected_tables = expected_operation.get("expected_public_table_names")
        if type(expected_tables) is not tuple or len(expected_tables) != 19:
            raise ValueError
        expected_manifest = [f"public.{name}" for name in expected_tables]
        if receipt.get("public_table_manifest") != expected_manifest:
            raise ValueError
        table_before = receipt.get("table_digests_before")
        table_after = receipt.get("table_digests_after")
        expected_keys = set(expected_manifest)
        if type(table_before) is not dict or type(table_after) is not dict:
            raise ValueError
        if set(table_before) != expected_keys or set(table_after) != expected_keys:
            raise ValueError
        if table_before != table_after:
            raise ValueError
        for digest in table_before.values():
            _require_exact_keys(digest, {'row_count', 'sha256'})
            if (
                type(digest) is not dict
                or not _strict_int(digest.get("row_count"))
                or digest["row_count"] < 0
            ):
                raise ValueError
            _require_sha256(digest.get("sha256"))
        if (
            table_before["public.aggregated_listings"].get("row_count") != 789
            or table_before["public.catalog_handoff_metadata"].get("row_count") != 789
        ):
            raise ValueError
        for name in ("view_digest_before", "view_digest_after"):
            view_digest = receipt.get(name)
            _require_exact_keys(view_digest, {'row_count', 'sha256'})
            if type(view_digest) is not dict or not _strict_int(view_digest.get("row_count"), 789):
                raise ValueError
            _require_sha256(view_digest.get("sha256"))
        if receipt["view_digest_before"] != receipt["view_digest_after"]:
            raise ValueError

        checks = receipt.get("checks")
        if type(checks) is not dict or set(checks) != {f"AC{i}" for i in range(1, 7)}:
            raise ValueError
        if any(type(value) is not bool or value is not True for value in checks.values()):
            raise ValueError
        readonly = receipt.get("readonly_probe")
        if (
            type(readonly) is not dict
            or set(readonly) != {"transaction_read_only", "dml_rejected"}
            or type(readonly.get("transaction_read_only")) is not bool
            or type(readonly.get("dml_rejected")) is not bool
            or readonly["transaction_read_only"] is not True
            or readonly["dml_rejected"] is not True
        ):
            raise ValueError

        counts = receipt.get("counts")
        if type(counts) is not dict or set(counts) != {"http", "api", "browser"}:
            raise ValueError
        for layer in ("http", "api"):
            values = counts.get(layer)
            _require_exact_keys(values, {'rows', 'unique_ids', 'pages'})
            if (
                type(values) is not dict
                or not _strict_int(values.get("rows"), 789)
                or not _strict_int(values.get("unique_ids"), 789)
                or not _strict_int(values.get("pages"))
                or values["pages"] < 1
            ):
                raise ValueError
        browser_counts = counts.get("browser")
        _require_exact_keys(browser_counts, {'rows', 'unique_ids', 'missing_positions'})
        if (
            type(browser_counts) is not dict
            or not _strict_int(browser_counts.get("rows"), 789)
            or not _strict_int(browser_counts.get("unique_ids"), 789)
            or not _strict_int(browser_counts.get("missing_positions"), 2)
        ):
            raise ValueError

        browser = receipt.get("browser")
        _require_exact_keys(browser, {'schema_version', 'status', 'evidence_kind', 'operation_id',
            'expected_public_data_sha256', 'actual_ids_sha256', 'api_origin', 'ui_origin',
            'source_catalog_count', 'unique_listing_count', 'missing_position_count',
            'positioned_listing_count', 'actual_positioned_members_sha256',
            'visible_checks', 'external_attempts'})
        if type(browser) is not dict:
            raise ValueError
        if browser.get("schema_version") != 2 or type(browser.get("schema_version")) is not int:
            raise ValueError
        if browser.get("status") != "REAL_CATALOG_BROWSER_VERIFIED":
            raise ValueError
        if browser.get("evidence_kind") != ACCEPTANCE_EVIDENCE:
            raise ValueError
        if browser.get("operation_id") != operation_id:
            raise ValueError
        if browser.get("expected_public_data_sha256") != expected_public_hash:
            raise ValueError
        if browser.get("actual_ids_sha256") != expected_ids_hash:
            raise ValueError
        if browser.get("api_origin") != f"http://{API_HOST}:{API_PORT}":
            raise ValueError
        if browser.get("ui_origin") != f"http://{UI_HOST}:{UI_PORT}":
            raise ValueError
        if not _strict_int(browser.get("source_catalog_count"), 789):
            raise ValueError
        if not _strict_int(browser.get("unique_listing_count"), 789):
            raise ValueError
        if not _strict_int(browser.get("missing_position_count"), 2):
            raise ValueError
        if not _strict_int(browser.get("positioned_listing_count"), 787):
            raise ValueError
        _require_sha256(browser.get("actual_positioned_members_sha256"))
        if browser.get("actual_positioned_members_sha256") != expected_positioned_members_sha256:
            raise ValueError
        visible_checks = browser.get("visible_checks")
        required_visible = {
            "original_titles",
            "null_area",
            "partial_description",
            "withheld_description",
            "contact_href",
            "missing_position_selectable",
            "missing_position_has_no_pin",
            "missing_position_route_disabled",
            "actual_cluster_membership",
        }
        if type(visible_checks) is not dict or set(visible_checks) != required_visible:
            raise ValueError
        if any(type(value) is not bool or value is not True for value in visible_checks.values()):
            raise ValueError
        if not _strict_int(browser.get("external_attempts"), 0):
            raise ValueError
        if not _strict_int(receipt.get("external_attempts"), 0):
            raise ValueError
        _require_sha256(receipt.get("browser_receipt_sha256"))
        if receipt["browser_receipt_sha256"] != canonical_json_sha256(browser):
            raise ValueError
        _require_sha256(receipt.get("screenshot_sha256"))
    except Exception:
        raise ValueError("Acceptance receipt verification failed.") from None
    return None


def discover_source_pin_paths(project_root: Path) -> tuple[str, ...]:
    """Return the exact fixed and directory-derived source pin set."""
    root = Path(project_root).resolve()
    paths = {"scripts/mobility_catalog_acceptance.py", *CODE_PIN_FILES}
    for relative_root in CODE_PIN_ROOTS:
        directory = root / Path(relative_root)
        if not directory.is_dir():
            raise ValueError("Acceptance source pins are incomplete.")
        suffixes = {".py"} if relative_root == "apps/api/app/mobility" else {".ts", ".tsx"}
        for candidate in directory.rglob("*"):
            if candidate.is_file() and candidate.suffix in suffixes:
                resolved = candidate.resolve()
                if not resolved.is_relative_to(root):
                    raise ValueError("Acceptance source pins are invalid.")
                paths.add(candidate.relative_to(root).as_posix())
    for relative in paths:
        candidate = root / Path(relative)
        if not candidate.is_file() or candidate.is_symlink():
            raise ValueError("Acceptance source pins are incomplete.")
    return tuple(sorted(paths))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_catalog_phase_gate() -> None:
    try:
        path = PROJECT_ROOT / ".codex-gate.json"
        if path.is_symlink() or not path.is_file() or _sha256_file(path) != CATALOG_PHASE_GATE_SHA256:
            raise ValueError
    except Exception:
        raise ValueError("Acceptance catalog gate verification failed.") from None


def _hash_source_files() -> tuple[str, str]:
    catalog_digest = _sha256_file(SOURCE_CATALOG_PATH)
    zip_digest = _sha256_file(SOURCE_ZIP_PATH)
    if catalog_digest != SOURCE_CATALOG_SHA256 or zip_digest != SOURCE_ZIP_SHA256:
        raise ValueError("Pinned source verification failed.")
    return catalog_digest, zip_digest


def _pinned_public_table_names() -> tuple[str, ...]:
    if _sha256_file(SOURCE_ZIP_PATH) != SOURCE_ZIP_SHA256:
        raise ValueError("Pinned source verification failed.")
    try:
        with zipfile.ZipFile(SOURCE_ZIP_PATH, "r") as archive:
            entries = [item for item in archive.infolist() if item.filename == "SOURCE_BASELINE.json"]
            if len(entries) != 1:
                raise ValueError
            document = json.loads(archive.read(entries[0]).decode("utf-8"))
        source_tables = document.get("tables")
        if type(source_tables) is not dict or set(source_tables) != SOURCE_BASELINE_TABLES:
            raise ValueError
        expected = set(source_tables)
        expected.add("catalog_handoff_metadata")
        if len(expected) != 19:
            raise ValueError
        return tuple(sorted(expected))
    except Exception:
        raise ValueError("Pinned source manifest verification failed.") from None


def _read_source_catalog() -> list[dict[str, object]]:
    _hash_source_files()
    rows: list[dict[str, object]] = []
    try:
        with SOURCE_CATALOG_PATH.open("r", encoding="utf-8", newline="") as stream:
            for line in stream:
                if not line.strip():
                    continue
                value = json.loads(line)
                if type(value) is not dict:
                    raise ValueError
                rows.append(value)
        if len(rows) != 789:
            raise ValueError
        return rows
    except Exception:
        raise ValueError("Pinned source catalog verification failed.") from None


def _canonical_json_text(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def _operation_context(
    config: RuntimeConfig,
    table_names: tuple[str, ...],
) -> dict[str, object]:
    return {
        "operation_id": config.operation_id,
        "container": config.container,
        "project": config.project,
        "volume": config.volume,
        "host": config.host,
        "port": config.port,
        "database": config.database,
        "role": config.user,
        "expected_public_table_names": table_names,
    }


def _workspace_evidence_hashes(
    runtime_dir: Path,
) -> tuple[dict[str, str], dict[str, str]]:
    source_hashes = {
        "source_catalog_sha256": _sha256_file(SOURCE_CATALOG_PATH),
        "source_zip_sha256": _sha256_file(SOURCE_ZIP_PATH),
    }
    if source_hashes != {
        "source_catalog_sha256": SOURCE_CATALOG_SHA256,
        "source_zip_sha256": SOURCE_ZIP_SHA256,
    }:
        raise ValueError("Pinned source verification failed.")
    code_hashes = {
        relative: _sha256_file(PROJECT_ROOT / Path(relative))
        for relative in discover_source_pin_paths(PROJECT_ROOT)
    }
    artifact_hashes = {
        relative: _sha256_file(PROJECT_ROOT / Path(relative))
        for relative in PUBLIC_ARTIFACTS
    }
    artifact_hashes["runtime_config_sha256"] = _sha256_file(
        runtime_dir / RUNTIME_CONFIG_NAME
    )
    return source_hashes, code_hashes | artifact_hashes


def _verify_expected_public_file(
    path: Path,
    source_rows: list[dict[str, object]],
    operation_id: str,
) -> tuple[list[dict[str, object]], str, str]:
    expected_rows = [_source_public_row(row) for row in source_rows]
    expected_rows.sort(key=lambda row: row["id"])
    canonical = _canonical_json_text(expected_rows)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise ValueError("Expected browser data is invalid.") from None
    if (
        type(envelope) is not dict
        or envelope.get("schema_version") != 1
        or type(envelope.get("schema_version")) is not int
        or envelope.get("operation_id") != operation_id
        or envelope.get("canonical_public_json") != canonical
        or envelope.get("public_dto_sha256") != digest
    ):
        raise ValueError("Expected browser data is invalid.")
    return expected_rows, canonical, digest


def _verify_receipt(runtime_dir: Path) -> None:
    _verify_catalog_phase_gate()
    receipt_path = runtime_dir / REAL_ACCEPTANCE_NAME
    if not receipt_path.is_file():
        raise ValueError("Acceptance receipt is missing.")
    runtime_path = runtime_dir / RUNTIME_CONFIG_NAME
    raw_runtime = runtime_path.read_bytes()
    raw_config = json.loads(raw_runtime.decode("utf-8"))
    config = validate_runtime_config(raw_config)
    table_names = _pinned_public_table_names()
    source_rows = _read_source_catalog()
    source_hashes, hashes = _workspace_evidence_hashes(runtime_dir)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if type(receipt) is not dict:
        raise ValueError
    if receipt.get("source_catalog_sha256") != source_hashes["source_catalog_sha256"]:
        raise ValueError
    if receipt.get("source_zip_sha256") != source_hashes["source_zip_sha256"]:
        raise ValueError
    if receipt.get("code_sha256") != {
        name: value for name, value in hashes.items() if name in discover_source_pin_paths(PROJECT_ROOT)
    }:
        raise ValueError
    if receipt.get("spec_sha256") != hashes[PUBLIC_ARTIFACTS[0]]:
        raise ValueError
    if receipt.get("plan_sha256") != hashes[PUBLIC_ARTIFACTS[1]]:
        raise ValueError
    if receipt.get("gate_sha256") != hashes[PUBLIC_ARTIFACTS[2]]:
        raise ValueError
    if receipt.get("runtime_config_sha256") != hashes["runtime_config_sha256"]:
        raise ValueError

    browser_path = runtime_dir / BROWSER_RECEIPT_NAME
    screenshot_path = runtime_dir / SCREENSHOT_NAME
    browser_document = json.loads(browser_path.read_text(encoding="utf-8"))
    if receipt.get("browser") != browser_document:
        raise ValueError
    if receipt.get("browser_receipt_sha256") != canonical_json_sha256(browser_document):
        raise ValueError
    if receipt.get("screenshot_sha256") != _sha256_file(screenshot_path):
        raise ValueError
    expected_path = runtime_dir / EXPECTED_PUBLIC_DATA_NAME
    expected_rows, _, public_hash = _verify_expected_public_file(
        expected_path, source_rows, config.operation_id
    )
    if receipt.get("public_dto_sha256") != public_hash:
        raise ValueError
    if receipt.get("actual_ids_sha256") != canonical_json_sha256(
        sorted(row["id"] for row in expected_rows)
    ):
        raise ValueError
    operation = _operation_context(config, table_names)
    validate_real_receipt_document(
        receipt,
        expected_source_rows=source_rows,
        expected_code_pin_hashes={
            name: hashes[name] for name in discover_source_pin_paths(PROJECT_ROOT)
        },
        expected_operation=operation,
    )


def _write_json_exclusive(path: Path, value: object) -> None:
    encoded = (_canonical_json_text(value) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        raise ValueError("Private evidence write failed.") from None


def _require_exact_keys(value: object, expected: set[str]) -> None:
    if type(value) is not dict or set(value) != expected:
        raise ValueError('Evidence schema is invalid.')


def validate_clone_metadata(container: dict, volume: dict, config: RuntimeConfig) -> dict:
    """Validate observed inspect documents without persisting their sensitive fields."""
    try:
        config = validate_runtime_config(config)
        expected_labels = {
            'nckh.acceptance.operation': config.operation_id,
            'nckh.acceptance.catalog_sha256': SOURCE_CATALOG_SHA256,
            'com.docker.compose.project': config.project,
        }
        for labels in (container['Config']['Labels'], volume['Labels']):
            if any(labels.get(key) != value for key, value in expected_labels.items()):
                raise ValueError
        ports = {'5432/tcp': [{'HostIp': TARGET_HOST, 'HostPort': str(TARGET_PORT)}]}
        if (container['Name'] != '/' + config.container or container['Image'] != EXPECTED_IMAGE_ID
            or volume['Name'] != config.volume or volume['Driver'] != 'local'
            or container['State']['Running'] is not True
            or container['State']['Health']['Status'] != 'healthy'
            or container['HostConfig']['PortBindings'] != ports
            or container['NetworkSettings']['Ports'] != ports):
            raise ValueError
        data_mounts = [mount for mount in container['Mounts']
                       if mount.get('Destination') == '/var/lib/postgresql/data']
        if (len(data_mounts) != 1 or data_mounts[0].get('Type') != 'volume'
            or data_mounts[0].get('Name') != volume['Name'] or data_mounts[0].get('RW') is not True
            or sum(mount.get('Type') == 'volume' for mount in container['Mounts']) != 1):
            raise ValueError
        binding = container['NetworkSettings']['Ports']['5432/tcp'][0]
        return {'operation_id': container['Config']['Labels']['nckh.acceptance.operation'],
                'image_id': container['Image'],
                'source_catalog_sha256': volume['Labels']['nckh.acceptance.catalog_sha256'],
                'target': {'container': container['Name'][1:],
                           'project': container['Config']['Labels']['com.docker.compose.project'],
                           'volume': volume['Name'], 'host': binding['HostIp'],
                           'port': int(binding['HostPort']), 'database': config.database, 'role': config.user}}
    except Exception:
        raise ValueError('Acceptance clone identity is invalid.') from None


def _inspect_clone_identity(config: RuntimeConfig) -> dict:
    config = validate_runtime_config(config)
    documents = []
    try:
        for kind, name in (('container', config.container), ('volume', config.volume)):
            result = subprocess.run(['docker', kind, 'inspect', name], capture_output=True,
                                    text=True, timeout=10, check=False, env=_minimal_child_env())
            if result.returncode != 0:
                raise ValueError
            document = json.loads(result.stdout)
            if type(document) is not list or len(document) != 1 or type(document[0]) is not dict:
                raise ValueError
            documents.append(document[0])
        return validate_clone_metadata(*documents, config)
    except Exception:
        raise ValueError('Acceptance clone identity is invalid.') from None


def validate_reader_privileges(snapshot: dict) -> None:
    try:
        if (snapshot['database_name'] != TARGET_DATABASE or snapshot['role_name'] != TARGET_ROLE
            or not _strict_int(snapshot['server_port'], 5432)
            or snapshot['read_only'] != 'on' or snapshot['default_read_only'] != 'on'):
            raise ValueError
        for field in ('superuser', 'createdb', 'createrole', 'bypassrls', 'database_create',
                      'schema_create', 'dangerous_membership', 'any_write'):
            if snapshot[field] is not False:
                raise ValueError
        if snapshot['all_select'] is not True:
            raise ValueError
    except Exception:
        raise ValueError('Acceptance database identity is invalid.') from None


def _db_connection_identity(engine) -> dict:
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql(
                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
            )
            connection.exec_driver_sql("SET TIME ZONE 'UTC'")
            row = connection.execute(
                text(
                    "SELECT current_database() AS database_name, "
                    "current_user AS role_name, "
                    "inet_server_port() AS server_port, "
                    "current_setting('transaction_read_only') AS read_only, "
                    "current_setting('default_transaction_read_only') AS default_read_only, "
                    "r.rolsuper AS superuser, r.rolcreatedb AS createdb, "
                    "r.rolcreaterole AS createrole, r.rolbypassrls AS bypassrls, "
                    "has_database_privilege(current_user,current_database(),'CREATE') AS database_create, "
                    "has_schema_privilege(current_user,'public','CREATE') AS schema_create, "
                    "EXISTS (SELECT 1 FROM pg_roles m WHERE pg_has_role(current_user,m.oid,'MEMBER') "
                    "AND (m.rolsuper OR m.rolcreatedb OR m.rolcreaterole OR m.rolbypassrls "
                    "OR m.rolname='pg_write_all_data')) AS dangerous_membership, "
                    "(SELECT coalesce(bool_and(has_table_privilege(current_user,c.oid,'SELECT')),false) "
                    "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                    "WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f')) AS all_select, "
                    "(SELECT coalesce(bool_or(has_table_privilege(current_user,c.oid, "
                    "'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')),false) "
                    "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                    "WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f')) AS any_write "
                    "FROM pg_roles r WHERE r.rolname=current_user"
                )
            ).mappings().one()
            validate_reader_privileges(dict(row))
            return {'database': row['database_name'], 'role': row['role_name']}
    except Exception:
        raise ValueError("Acceptance database identity is invalid.") from None


def _read_public_relation_names(connection) -> tuple[str, ...]:
    rows = connection.execute(
        text(
            "SELECT c.relname "
            "FROM pg_class AS c "
            "JOIN pg_namespace AS n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') "
            "ORDER BY c.relname"
        )
    ).scalars().all()
    return tuple(str(name) for name in rows)


def _hash_public_tables(engine, expected_names: tuple[str, ...]) -> dict[str, object]:
    table_digests: dict[str, dict[str, object]] = {}
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql(
                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
            )
            connection.exec_driver_sql("SET TIME ZONE 'UTC'")
            actual_names = _read_public_relation_names(connection)
            if actual_names != expected_names:
                raise ValueError
            preparer = connection.dialect.identifier_preparer
            for name in expected_names:
                identifier = preparer.quote(name)
                records = connection.execute(
                    text(f"SELECT to_jsonb(t)::text FROM public.{identifier} AS t")
                ).scalars().all()
                record_strings = [record for record in records]
                table_digests[f"public.{name}"] = {
                    "row_count": len(record_strings),
                    "sha256": canonical_records_sha256(record_strings),
                }
        aggregate_values = [
            [name, value["row_count"], value["sha256"]]
            for name, value in sorted(table_digests.items())
        ]
        return {
            "table_digests": table_digests,
            "aggregate_sha256": canonical_json_sha256(aggregate_values),
        }
    except Exception:
        raise ValueError("Acceptance public data digest failed.") from None


def _hash_catalog_view(engine) -> dict[str, object]:
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql(
                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
            )
            connection.exec_driver_sql("SET TIME ZONE 'UTC'")
            records = connection.execute(
                text(
                    "SELECT to_jsonb(v)::text "
                    "FROM public.catalog_handoff_v1 AS v "
                    "WHERE v.package_id = :package_id "
                    "AND v.catalog_sha256 = :catalog_sha256"
                ),
                {
                    "package_id": PINNED_PACKAGE_ID,
                    "catalog_sha256": SOURCE_CATALOG_SHA256,
                },
            ).scalars().all()
        return {
            "row_count": len(records),
            "sha256": canonical_records_sha256(list(records)),
        }
    except Exception:
        raise ValueError("Acceptance catalog view digest failed.") from None


def _catalog_sql_metrics(engine) -> dict[str, int]:
    statement = text(
        """
        SELECT COUNT(*) AS catalog_count,
               COUNT(*) FILTER (WHERE LOWER(BTRIM(COALESCE(housing_type, ''))) = 'room') AS room_count,
               COUNT(*) FILTER (WHERE LOWER(BTRIM(COALESCE(housing_type, ''))) = 'mini_house') AS mini_house_count,
               COUNT(*) FILTER (WHERE LOWER(BTRIM(COALESCE(housing_type, ''))) = 'studio') AS studio_count,
               COUNT(*) FILTER (WHERE LOWER(BTRIM(COALESCE(housing_type, ''))) NOT IN ('room', 'mini_house', 'studio')) AS unknown_count,
               COUNT(*) FILTER (WHERE area IS NOT NULL) AS area_value_count,
               COUNT(*) FILTER (WHERE area IS NULL) AS area_null_count,
               COUNT(*) FILTER (WHERE geom IS NOT NULL) AS position_count,
               COUNT(*) FILTER (WHERE geom IS NULL) AS position_null_count
        FROM public.catalog_handoff_v1
        WHERE package_id = :package_id AND catalog_sha256 = :catalog_sha256
        """
    )
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql(
                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
            )
            row = connection.execute(
                statement,
                {
                    "package_id": PINNED_PACKAGE_ID,
                    "catalog_sha256": SOURCE_CATALOG_SHA256,
                },
            ).mappings().one()
        metrics = {key: int(value) for key, value in row.items()}
        if metrics != {
            "catalog_count": 789,
            "room_count": 614,
            "mini_house_count": 168,
            "studio_count": 3,
            "unknown_count": 4,
            "area_value_count": 153,
            "area_null_count": 636,
            "position_count": 787,
            "position_null_count": 2,
        }:
            raise ValueError
        return metrics
    except Exception:
        raise ValueError("Acceptance catalog SQL counts do not match.") from None


def _readonly_dml_probe(engine) -> None:
    connection = None
    try:
        connection = engine.connect()
        connection.exec_driver_sql(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
        )
        connection.exec_driver_sql("SET TIME ZONE 'UTC'")
        identity = connection.exec_driver_sql(
            "SELECT current_database() AS database_name, "
            "current_user AS role_name, "
            "current_setting('transaction_read_only') AS read_only"
        ).mappings().one()
        mode = connection.exec_driver_sql("SHOW transaction_read_only").scalar_one()
        if (
            identity["database_name"] != TARGET_DATABASE
            or identity["role_name"] != TARGET_ROLE
            or str(identity["read_only"]).lower() != "on"
            or str(mode).lower() != "on"
        ):
            connection.rollback()
            raise ValueError
        try:
            connection.exec_driver_sql("SELECT id FROM public.aggregated_listings LIMIT 1")
        except Exception:
            connection.rollback()
            raise ValueError("Acceptance reader identity check failed.") from None
        try:
            connection.execute(
                text("UPDATE public.aggregated_listings SET id = id WHERE false")
            )
        except Exception as refusal:
            connection.rollback()
            original = getattr(refusal, "orig", None) or refusal
            sqlstate = (
                getattr(original, "sqlstate", None)
                or getattr(original, "pgcode", None)
            )
            if sqlstate in {"25006", "42501"}:
                return
            raise ValueError("Acceptance reader DML refusal probe failed.") from None
        connection.rollback()
        raise ValueError("Acceptance reader DML refusal probe failed.")
    except ValueError:
        raise ValueError("Acceptance reader DML refusal probe failed.") from None
    except Exception:
        if connection is not None:
            connection.rollback()
        raise ValueError("Acceptance reader DML refusal probe failed.") from None
    finally:
        if connection is not None:
            connection.close()


async def _http_get_json(client: httpx.AsyncClient, path: str) -> object:
    try:
        response = await client.get(path, timeout=3.0)
        if response.status_code != 200:
            raise ValueError
        return response.json()
    except Exception:
        raise ValueError("Acceptance HTTP read failed.") from None


async def _http_post_json(client: httpx.AsyncClient, path: str, payload: dict[str, object]) -> object:
    try:
        response = await client.post(path, json=payload, timeout=3.0)
        if response.status_code != 200:
            raise ValueError
        return response.json()
    except Exception:
        raise ValueError("Acceptance HTTP read failed.") from None


def _read_real_http_catalog(source_rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], dict[str, object]]:
    async def fetch():
        async with httpx.AsyncClient(
            base_url=f"http://{API_HOST}:{API_PORT}",
            trust_env=False,
            follow_redirects=False,
            timeout=3.0,
        ) as client:
            campuses = await _http_get_json(client, "/mobility/campuses")
            if type(campuses) is not list or {item.get("id") for item in campuses if type(item) is dict} != {
                "khu_i",
                "khu_ii",
                "khu_iii",
            }:
                raise ValueError("Acceptance campus response is invalid.")
            actual_rows: list[dict[str, object]] = []
            page_count = 0
            for page in range(1, 9):
                document = await _http_get_json(
                    client, f"/mobility/listings?page={page}&size=100"
                )
                if type(document) is not dict:
                    raise ValueError
                if (
                    document.get("total") != 789
                    or document.get("page") != page
                    or document.get("size") != 100
                    or type(document.get("items")) is not list
                ):
                    raise ValueError
                actual_rows.extend(document["items"])
                page_count += 1
            if len(actual_rows) != 789:
                raise ValueError

            expected_rows = [_source_public_row(row) for row in source_rows]
            expected_rows.sort(key=lambda item: item["id"])
            positioned = next(row for row in expected_rows if row["position"] is not None)
            missing = [row for row in expected_rows if row["position"] is None]
            if len(missing) != 2:
                raise ValueError

            route = await _http_post_json(
                client,
                "/mobility/routes",
                {
                    "listing_id": positioned["id"],
                    "campus_id": "khu_i",
                    "requested_mode": "MOTORBIKE",
                },
            )
            if (
                type(route) is not dict
                or route.get("status") != "NOT_CONFIGURED"
                or route.get("duration_seconds") is not None
                or route.get("distance_meters") is not None
                or route.get("polyline") is not None
                or route.get("evidence_kind") != "NONE"
            ):
                raise ValueError
            nearby = await _http_post_json(
                client,
                "/mobility/nearby",
                {"listing_id": positioned["id"], "radius_m": 1000, "categories": ["grocery"]},
            )
            if (
                type(nearby) is not dict
                or nearby.get("status") != "NOT_CONFIGURED"
                or nearby.get("items") != []
                or nearby.get("evidence_kind") != "NONE"
            ):
                raise ValueError

            for row in missing:
                route_missing = await _http_post_json(
                    client,
                    "/mobility/routes",
                    {
                        "listing_id": row["id"],
                        "campus_id": "khu_i",
                        "requested_mode": "MOTORBIKE",
                    },
                )
                nearby_missing = await _http_post_json(
                    client,
                    "/mobility/nearby",
                    {"listing_id": row["id"], "radius_m": 1000, "categories": ["grocery"]},
                )
                if (
                    type(route_missing) is not dict
                    or route_missing.get("status") != "LOCATION_UNAVAILABLE"
                    or route_missing.get("duration_seconds") is not None
                    or route_missing.get("distance_meters") is not None
                    or route_missing.get("polyline") is not None
                    or type(nearby_missing) is not dict
                    or nearby_missing.get("status") != "LOCATION_UNAVAILABLE"
                    or nearby_missing.get("items") != []
                ):
                    raise ValueError
            return actual_rows, {
                "http": {
                    "rows": len(actual_rows),
                    "unique_ids": len({row.get("id") for row in actual_rows if type(row) is dict}),
                    "pages": page_count,
                },
                "missing_position_count": len(missing),
                "source_rows": expected_rows,
            }

    try:
        return asyncio.run(fetch())
    except Exception:
        raise ValueError("Acceptance HTTP verification failed.") from None


def _create_test_api_app(engine):
    """Build only the test mobility router; never import the production app."""
    api_root = PROJECT_ROOT / "apps" / "api"
    if str(api_root) not in sys.path:
        sys.path.insert(0, str(api_root))
    from fastapi import FastAPI
    from app.mobility.catalog_repo import CatalogRepo
    from app.mobility.providers.open_config import OpenMobilitySettings
    from app.mobility.router import install_mobility
    from pydantic import SecretStr

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    settings = OpenMobilitySettings(
        _env_file=None,
        enabled=True,
        live_enabled=False,
        google_maps_enabled=False,
        routing_provider="disabled",
        places_provider="disabled",
        geocoder_provider="disabled",
        ors_api_key=SecretStr(""),
        ors_base_url="",
        overpass_url="",
        nominatim_url="",
        provider_policies={},
        expected_policy_hashes={},
        tiles_enabled=False,
        tile_url="",
        tile_attribution="",
        allowed_tile_origin="",
    )
    install_mobility(
        app,
        catalog=CatalogRepo(engine),
        enabled=True,
        open_settings=settings,
    )
    return app


def _serve_api(runtime_dir: Path) -> int:
    _verify_catalog_phase_gate()
    raw = json.loads((runtime_dir / RUNTIME_CONFIG_NAME).read_text(encoding="utf-8"))
    config = validate_runtime_config(raw)
    _inspect_clone_identity(config)
    engine = connect_readonly(config)
    try:
        import uvicorn

        app = _create_test_api_app(engine)
        uvicorn.run(
            app,
            host=API_HOST,
            port=API_PORT,
            log_level="error",
            access_log=False,
            server_header=False,
            date_header=False,
            limit_concurrency=50,
            timeout_keep_alive=3,
            timeout_graceful_shutdown=3,
        )
        return 0
    finally:
        engine.dispose()


def _assert_port_free(host: str, port: int) -> None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1.0)
            probe.bind((host, port))
    except OSError:
        raise ValueError("Acceptance service port is unavailable.") from None


def _minimal_child_env(*, web: bool = False) -> dict[str, str]:
    keep = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "COMSPEC"}
    env = {key: value for key, value in os.environ.items() if key.upper() in keep}
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(PROJECT_ROOT / "apps" / "api")
    env["DOCKER_CONFIG"] = str(PROJECT_ROOT / ".superpowers/sdd/2026-10-05-open-mobility-agent-plan/docker-readonly-config")
    env["GOOGLE_MAPS_ENABLED"] = "false"
    env["MOBILITY_LIVE_ENABLED"] = "false"
    env["MOBILITY_ROUTING_PROVIDER"] = "disabled"
    env["MOBILITY_PLACES_PROVIDER"] = "disabled"
    env["MOBILITY_GEOCODER_PROVIDER"] = "disabled"
    env["MOBILITY_ORS_API_KEY"] = ""
    env["MOBILITY_ORS_BASE_URL"] = ""
    env["MOBILITY_OVERPASS_URL"] = ""
    env["MOBILITY_NOMINATIM_URL"] = ""
    env["MOBILITY_TILES_ENABLED"] = "false"
    env["MOBILITY_TILE_URL"] = ""
    env["MOBILITY_TILE_ATTRIBUTION"] = ""
    env["MOBILITY_ALLOWED_TILE_ORIGIN"] = ""
    env["GOOGLE_MAPS_API_KEY"] = ""
    env["GOOGLE_ROUTES_API_KEY"] = ""
    env["GOOGLE_PLACES_API_KEY"] = ""
    env["ORS_API_KEY"] = ""
    if web:
        env["NODE_ENV"] = "production"
        env["NEXT_TELEMETRY_DISABLED"] = "1"
        env["MOBILITY_ENABLED"] = "true"
        env["API_INTERNAL_URL"] = f"http://{API_HOST}:{API_PORT}"
        env.pop("NEXT_PUBLIC_API_URL", None)
    return env


def _start_owned_process(command: list[str], *, cwd: Path, env: dict[str, str]):
    options: dict[str, object] = {
        "cwd": str(cwd),
        "env": env,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    try:
        return subprocess.Popen(command, **options)
    except Exception:
        raise ValueError("Acceptance service could not start.") from None


def _wait_for_local_http(process, url: str, *, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise ValueError("Acceptance service stopped before readiness.")
        try:
            response = httpx.get(url, timeout=1.0, trust_env=False, follow_redirects=False)
            if response.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.25)
    raise ValueError("Acceptance service readiness timed out.")


def _stop_owned_process(process) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
            if result.returncode != 0 and process.poll() is None:
                process.kill()
        else:
            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
            process.wait(timeout=3)
        except Exception:
            raise ValueError("Owned acceptance service cleanup failed.") from None


def _run_real_browser(
    runtime_dir: Path,
    source_rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object], dict[str, object]]:
    node = shutil.which("node")
    web_root = PROJECT_ROOT / "apps" / "web"
    next_cli = web_root / "node_modules" / "next" / "dist" / "bin" / "next"
    if not node or not next_cli.is_file() or not (web_root / ".next" / "BUILD_ID").is_file():
        raise ValueError("Installed web runtime is unavailable.")
    _assert_port_free(UI_HOST, UI_PORT)
    expected_path = runtime_dir / EXPECTED_PUBLIC_DATA_NAME
    browser_path = runtime_dir / BROWSER_RECEIPT_NAME
    screenshot_path = runtime_dir / SCREENSHOT_NAME
    if browser_path.exists() or screenshot_path.exists():
        raise ValueError("Acceptance evidence already exists.")

    api_process = None
    web_process = None
    try:
        _assert_port_free(API_HOST, API_PORT)
        api_process = _start_owned_process(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "serve-api",
                "--runtime-dir",
                str(runtime_dir),
            ],
            cwd=PROJECT_ROOT,
            env=_minimal_child_env(),
        )
        _wait_for_local_http(
            api_process,
            f"http://{API_HOST}:{API_PORT}/mobility/campuses",
            timeout_seconds=45,
        )
        actual_rows, http_summary = _read_real_http_catalog(source_rows)
        web_process = _start_owned_process(
            [
                node,
                str(next_cli),
                "start",
                "--hostname",
                UI_HOST,
                "--port",
                str(UI_PORT),
            ],
            cwd=web_root,
            env=_minimal_child_env(web=True),
        )
        _wait_for_local_http(
            web_process,
            f"http://{UI_HOST}:{UI_PORT}/map",
            timeout_seconds=60,
        )
        helper = PROJECT_ROOT / "apps" / "web" / "e2e" / "mobility-catalog-acceptance.cjs"
        result = subprocess.run(
            [
                node,
                str(helper),
                str(expected_path),
                str(browser_path),
                str(screenshot_path),
            ],
            cwd=web_root,
            env=_minimal_child_env(web=True),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=150,
            check=False,
        )
        if result.returncode != 0 or result.stderr:
            raise ValueError("Acceptance browser verification failed.")
        browser = json.loads(browser_path.read_text(encoding="utf-8"))
        if type(browser) is not dict:
            raise ValueError
        return actual_rows, {
            "http": http_summary["http"],
            "api": http_summary["http"],
            "browser": {
                "rows": browser.get("source_catalog_count"),
                "unique_ids": browser.get("unique_listing_count"),
                "missing_positions": browser.get("missing_position_count"),
            },
        }, browser
    finally:
        _stop_owned_process(web_process)
        _stop_owned_process(api_process)


def validate_runtime_acl(snapshot: dict) -> None:
    try:
        sid = snapshot['current_sid']
        if type(sid) is not str or not sid or snapshot['owner_sid'] != sid or snapshot['protected'] is not True:
            raise ValueError
        rules = snapshot['rules']
        if type(rules) is not list or not rules:
            raise ValueError
        for rule in rules:
            if (rule['sid'] != sid or rule['allow'] is not True or rule['inherited'] is not False
                or type(rule['rights']) is not int or rule['rights'] & 2032127 != 2032127):
                raise ValueError
    except Exception:
        raise ValueError('Private runtime ACL is invalid.') from None


def _runtime_acl_snapshot(path: Path) -> dict:
    command = r"""$ErrorActionPreference = 'Stop'
$sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$acl=Get-Acl -LiteralPath $env:NCKH_ACCEPTANCE_PATH
$rules=@($acl.Access | ForEach-Object {
    @{sid=$_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value;
      allow=($_.AccessControlType -eq 'Allow'); inherited=$_.IsInherited; rights=[int]$_.FileSystemRights}
})
@{current_sid=$sid;owner_sid=$acl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value;
  protected=$acl.AreAccessRulesProtected;rules=$rules} | ConvertTo-Json -Depth 5 -Compress
"""
    try:
        if os.name != 'nt':
            raise ValueError
        environment = _minimal_child_env()
        environment['NCKH_ACCEPTANCE_PATH'] = str(path)
        result = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', command],
                                env=environment, capture_output=True, text=True, timeout=10, check=False)
        if result.returncode != 0:
            raise ValueError
        return json.loads(result.stdout)
    except Exception:
        raise ValueError('Private runtime ACL is invalid.') from None


def _runtime_directory(path: str | Path) -> Path:
    runtime_dir = Path(path).expanduser()
    if not runtime_dir.is_absolute() or runtime_dir != APPROVED_RUNTIME_DIR:
        raise ValueError('Private acceptance runtime directory is invalid.')
    if not runtime_dir.is_dir() or runtime_dir.is_symlink():
        raise ValueError("Private acceptance runtime directory is unavailable.")
    resolved = runtime_dir.resolve(strict=True)
    if resolved.is_relative_to(PROJECT_ROOT):
        raise ValueError("Private acceptance runtime directory is invalid.")
    if resolved != APPROVED_RUNTIME_DIR:
        raise ValueError('Private acceptance runtime directory is invalid.')
    for ancestor in (runtime_dir, *runtime_dir.parents):
        if getattr(ancestor.lstat(), 'st_file_attributes', 0) & 0x400:
            raise ValueError('Private runtime reparse path is invalid.')
    validate_runtime_acl(_runtime_acl_snapshot(resolved))
    return resolved


def _load_runtime_config(runtime_dir: Path) -> tuple[RuntimeConfig, bytes]:
    config_path = runtime_dir / RUNTIME_CONFIG_NAME
    raw_bytes = config_path.read_bytes()
    raw = json.loads(raw_bytes.decode("utf-8"))
    config = validate_runtime_config(raw)
    return config, raw_bytes


def _write_expected_public_file(
    runtime_dir: Path,
    operation_id: str,
    expected_rows: list[dict[str, object]],
) -> str:
    canonical = _canonical_json_text(expected_rows)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    envelope = {
        "schema_version": 1,
        "operation_id": operation_id,
        "public_dto_sha256": digest,
        "canonical_public_json": canonical,
    }
    _write_json_exclusive(runtime_dir / EXPECTED_PUBLIC_DATA_NAME, envelope)
    return digest


def _verify_acceptance(runtime_dir: Path) -> dict[str, object]:
    _verify_catalog_phase_gate()
    runtime_dir = _runtime_directory(runtime_dir)
    if (runtime_dir / REAL_ACCEPTANCE_NAME).exists():
        raise ValueError("Acceptance receipt already exists.")
    for name in (EXPECTED_PUBLIC_DATA_NAME, BROWSER_RECEIPT_NAME, SCREENSHOT_NAME):
        if (runtime_dir / name).exists():
            raise ValueError("Acceptance evidence already exists.")

    config, runtime_bytes = _load_runtime_config(runtime_dir)
    table_names = _pinned_public_table_names()
    source_rows = _read_source_catalog()
    expected_rows = [_source_public_row(row) for row in source_rows]
    expected_rows.sort(key=lambda row: row["id"])
    if len(expected_rows) != 789:
        raise ValueError("Pinned source catalog verification failed.")
    _projection_metrics(expected_rows)

    source_hashes_before, hashes_before = _workspace_evidence_hashes(runtime_dir)
    if _sha256_file(SOURCE_CATALOG_PATH) != SOURCE_CATALOG_SHA256:
        raise ValueError("Pinned source verification failed.")
    observed_clone = _inspect_clone_identity(config)
    engine = connect_readonly(config)
    api_rows: list[dict[str, object]] = []
    evidence_counts: dict[str, object] = {}
    browser: dict[str, object] = {}
    table_before: dict[str, object] = {}
    view_before: dict[str, object] = {}
    try:
        observed_database = _db_connection_identity(engine)
        _catalog_sql_metrics(engine)
        table_before = _hash_public_tables(engine, table_names)
        view_before = _hash_catalog_view(engine)
        if view_before["row_count"] != 789:
            raise ValueError("Acceptance catalog view count is invalid.")
        _readonly_dml_probe(engine)

        expected_public_hash = _write_expected_public_file(
            runtime_dir, config.operation_id, expected_rows
        )
        api_rows, evidence_counts, browser = _run_real_browser(runtime_dir, source_rows)
        validate_catalog_projection(source_rows, api_rows)
        if browser.get("expected_public_data_sha256") != expected_public_hash:
            raise ValueError("Acceptance browser data binding is invalid.")
        if browser.get("actual_ids_sha256") != canonical_json_sha256(
            sorted(row["id"] for row in expected_rows)
        ):
            raise ValueError("Acceptance browser ID binding is invalid.")

        if _db_connection_identity(engine) != observed_database:
            raise ValueError('Acceptance database identity changed.')
        if _inspect_clone_identity(config) != observed_clone:
            raise ValueError('Acceptance clone identity changed.')
        table_after = _hash_public_tables(engine, table_names)
        view_after = _hash_catalog_view(engine)
        if table_before != table_after or view_before != view_after:
            raise ValueError("Acceptance clone data changed.")
    finally:
        engine.dispose()

    source_hashes_after, hashes_after = _workspace_evidence_hashes(runtime_dir)
    if source_hashes_before != source_hashes_after or hashes_before != hashes_after:
        raise ValueError("Acceptance pinned files changed during the run.")
    runtime_sha = hashlib.sha256(runtime_bytes).hexdigest()
    if hashes_before.get("runtime_config_sha256") != runtime_sha:
        raise ValueError("Acceptance runtime configuration changed.")
    code_paths = discover_source_pin_paths(PROJECT_ROOT)
    code_hashes = {name: hashes_before[name] for name in code_paths}
    public_hash = canonical_json_sha256(expected_rows)
    actual_ids_hash = canonical_json_sha256(sorted(row["id"] for row in api_rows))
    browser_hash = canonical_json_sha256(browser)
    screenshot_hash = _sha256_file(runtime_dir / SCREENSHOT_NAME)
    view_receipt_before = {
        "row_count": int(view_before["row_count"]),
        "sha256": str(view_before["sha256"]),
    }
    view_receipt_after = {
        "row_count": int(view_after["row_count"]),
        "sha256": str(view_after["sha256"]),
    }
    receipt: dict[str, object] = {
        "schema_version": 1,
        "operation_id": observed_clone['operation_id'],
        "status": ACCEPTANCE_STATUS,
        "evidence_kind": ACCEPTANCE_EVIDENCE,
        "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "target": {**observed_clone['target'], **observed_database},
        "image_id": observed_clone['image_id'],
        "source_catalog_sha256": source_hashes_before["source_catalog_sha256"],
        "source_zip_sha256": source_hashes_before["source_zip_sha256"],
        "code_sha256": code_hashes,
        "spec_sha256": hashes_before[PUBLIC_ARTIFACTS[0]],
        "plan_sha256": hashes_before[PUBLIC_ARTIFACTS[1]],
        "gate_sha256": hashes_before[PUBLIC_ARTIFACTS[2]],
        "runtime_config_sha256": runtime_sha,
        "source_catalog_count": 789,
        "actual_ids_sha256": actual_ids_hash,
        "public_dto_sha256": public_hash,
        "public_table_manifest": [f"public.{name}" for name in table_names],
        "table_digests_before": table_before["table_digests"],
        "table_digests_after": table_after["table_digests"],
        "view_digest_before": view_receipt_before,
        "view_digest_after": view_receipt_after,
        "checks": {f"AC{i}": True for i in range(1, 7)},
        "readonly_probe": {
            "transaction_read_only": True,
            "dml_rejected": True,
        },
        "counts": evidence_counts,
        "browser": browser,
        "browser_receipt_sha256": browser_hash,
        "screenshot_sha256": screenshot_hash,
        "external_attempts": browser.get("external_attempts"),
    }
    operation = _operation_context(config, table_names)
    validate_real_receipt_document(
        receipt,
        expected_source_rows=source_rows,
        expected_code_pin_hashes=code_hashes,
        expected_operation=operation,
    )
    _write_json_exclusive(runtime_dir / REAL_ACCEPTANCE_NAME, receipt)
    return receipt


class _QuietArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('Invalid acceptance arguments.')


def _argument_parser() -> argparse.ArgumentParser:
    parser = _QuietArgumentParser(description="Verify the isolated mobility catalog acceptance.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("verify", "verify-receipt", "serve-api"):
        subcommand = commands.add_parser(command)
        subcommand.add_argument("--runtime-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _argument_parser().parse_args(argv)
        runtime_dir = _runtime_directory(args.runtime_dir)
        if args.command == "verify":
            _verify_acceptance(runtime_dir)
            sys.stdout.write('{"status":"PASS","code":"REAL_CATALOG_POSTGRES_UI_VERIFIED"}\n')
            return 0
        if args.command == "verify-receipt":
            _verify_receipt(runtime_dir)
            sys.stdout.write('{"status":"PASS","code":"REAL_ACCEPTANCE_RECEIPT_VERIFIED"}\n')
            return 0
        if args.command == "serve-api":
            return _serve_api(runtime_dir)
    except Exception:
        sys.stdout.write(FAILURE_LINE + "\n")
        return 1
    sys.stdout.write(FAILURE_LINE + "\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
