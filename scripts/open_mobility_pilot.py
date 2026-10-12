"""Single-worker live demo on the read-only 5455 clone, never production.

The operator supplies a separately reviewed manifest digest. No secret is put
in argv, receipt, frontend environment or public artifact.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/api"))
from scripts import mobility_catalog_acceptance as acceptance
from app.mobility.providers.demo_policy import (
    DEMO_ENDPOINTS, build_demo_live_settings, demo_expected_policy_hashes,
)

API_ORIGIN = "http://127.0.0.1:8033"
UI_ORIGIN = "http://127.0.0.1:3033"
BUDGET = {"routes": 2, "nearby": 1, "geocode": 1, "tiles": 60}
PILOT_FILES = (
    "docs/planning/open-mobility-provider-policy.md",
    "scripts/open_mobility_pilot.py", "scripts/open_mobility_tile_pilot.cjs",
    "apps/api/tests/test_open_mobility_pilot_guard.py",
    "apps/api/tests/test_open_mobility_tile_pilot_guard.py",
    "apps/api/tests/test_mobility_runtime_policy.py",
)


def required_pin_paths():
    return tuple(sorted(set(acceptance.discover_source_pin_paths(ROOT)) | set(PILOT_FILES)))


def _compiled_web_pins(root):
    built = root / "apps/web/.next"
    paths = [built / "BUILD_ID"]
    for folder in (built / "server", built / "static"):
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError("Compiled web artifact unavailable.")
        paths.extend(path for path in folder.rglob("*") if path.is_file())
    paths.extend(path for path in built.glob("*.json") if path.is_file())
    if len(paths) > 10000 or not (built / "BUILD_ID").is_file():
        raise ValueError("Compiled web artifact unavailable.")
    for path in paths:
        for ancestor in (path, *path.parents):
            if getattr(ancestor.lstat(), "st_file_attributes", 0) & 0x400 or ancestor.is_symlink():
                raise ValueError("Compiled web artifact is not local.")
            if ancestor == root:
                break
    return {str(path.relative_to(built)).replace("\\", "/"): acceptance._sha256_file(path)
            for path in sorted(set(paths))}


def make_manifest(*, root=ROOT):
    return {
        "schema_version": 1, "endpoints": dict(DEMO_ENDPOINTS),
        "policy_hashes": demo_expected_policy_hashes(), "budget": dict(BUDGET),
        "single_worker": True,
        "compiled_web": _compiled_web_pins(root),
        "source_pins": {name: acceptance._sha256_file(root / name) for name in required_pin_paths()},
        "artifacts": {name: acceptance._sha256_file(root / name) for name in acceptance.PUBLIC_ARTIFACTS},
    }


def validate_manifest(document, expected_digest: str, *, root=ROOT):
    if (len(expected_digest) != 64 or
            acceptance.canonical_json_sha256(document) != expected_digest or
            document != make_manifest(root=root)):
        raise ValueError("Pilot manifest is not approved for these bytes.")


def web_environment():
    env = acceptance._minimal_child_env(web=True)
    env.update({
        "API_INTERNAL_URL": API_ORIGIN,
        "MOBILITY_TILES_ENABLED": "true",
        "MOBILITY_TILE_URL": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "MOBILITY_ALLOWED_TILE_ORIGIN": "https://tile.openstreetmap.org",
        "MOBILITY_TILE_ATTRIBUTION": "© OpenStreetMap contributors",
    })
    return env


class _WindowsBrowserJob:
    """Own a browser runner and every descendant until the handle is closed."""
    def __init__(self):
        if os.name != "nt":
            raise OSError("Windows job requested on non-Windows host")
        import win32api, win32job, win32process
        self._api, self._job, self._process = win32api, win32job, win32process
        self._handle = win32job.CreateJobObject(None, "")
        self._pi = None
        self._output_path = None
        self._assigned = False
        try:
            limits = win32job.QueryInformationJobObject(
                self._handle, win32job.JobObjectExtendedLimitInformation)
            limits["BasicLimitInformation"]["LimitFlags"] |= \
                win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(
                self._handle, win32job.JobObjectExtendedLimitInformation, limits)
        except Exception:
            self._api.CloseHandle(self._handle)
            self._handle = None
            raise

    def run(self, command, *, env, cwd):
        import win32con, win32file
        output_fd, output_name = tempfile.mkstemp(prefix="nckh-p5-browser-", suffix=".log")
        os.close(output_fd)
        self._output_path = Path(output_name)
        output = None
        stdin_handle = None
        try:
            output = win32file.CreateFile(str(self._output_path), win32con.GENERIC_WRITE,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE, None,
                win32con.OPEN_EXISTING, win32con.FILE_ATTRIBUTE_NORMAL, None)
            self._api.SetHandleInformation(output.handle, 1, 1)
            stdin_handle = win32file.CreateFile("NUL", win32con.GENERIC_READ,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE, None,
                win32con.OPEN_EXISTING, win32con.FILE_ATTRIBUTE_NORMAL, None)
            self._api.SetHandleInformation(stdin_handle.handle, 1, 1)
        except Exception:
            if output is not None:
                try: output.Close()
                except Exception: pass
            if stdin_handle is not None:
                try: stdin_handle.Close()
                except Exception: pass
            self._output_path.unlink(missing_ok=True)
            raise
        startup = self._process.STARTUPINFO()
        startup.dwFlags |= win32con.STARTF_USESHOWWINDOW | win32con.STARTF_USESTDHANDLES
        startup.wShowWindow = win32con.SW_HIDE
        startup.hStdOutput = output.handle
        startup.hStdError = output.handle
        startup.hStdInput = stdin_handle.handle
        command_line = subprocess.list2cmdline(command)
        try:
            self._pi = self._process.CreateProcess(
                None, command_line, None, None, True,
                win32con.CREATE_SUSPENDED | win32con.CREATE_NEW_PROCESS_GROUP,
                env, str(cwd), startup)
            self._job.AssignProcessToJobObject(self._handle, self._pi[0])
            self._assigned = True
            self._process.ResumeThread(self._pi[1])
            return self._pi
        except Exception:
            self.close()
            raise
        finally:
            output.Close()
            stdin_handle.Close()

    def terminate(self):
        if self._handle:
            self._job.TerminateJobObject(self._handle, 1)

    def close(self):
        unassigned_cleanup_failed = False
        if self._pi and not self._assigned:
            try: self._process.TerminateProcess(self._pi[0], 1)
            except Exception: unassigned_cleanup_failed = True
            try:
                import win32event
                if win32event.WaitForSingleObject(self._pi[0], 2000) != 0:
                    unassigned_cleanup_failed = True
            except Exception: unassigned_cleanup_failed = True
        if self._pi:
            for handle in self._pi[:2]:
                try: self._api.CloseHandle(handle)
                except Exception: pass
            self._pi = None
        if self._handle:
            self._api.CloseHandle(self._handle)
            self._handle = None
        if self._output_path:
            try: self._output_path.unlink(missing_ok=True)
            except Exception: pass
        if unassigned_cleanup_failed:
            raise OSError("Unassigned browser process cleanup not verified")

    def output(self):
        if not self._output_path or not self._output_path.exists(): return ""
        if self._output_path.stat().st_size > 1048576:
            raise ValueError("Browser aggregate output exceeds limit")
        return self._output_path.read_text(encoding="utf-8")

    def wait(self, timeout_ms):
        import win32event
        return win32event.WaitForSingleObject(self._pi[0], timeout_ms)

    def exit_code(self):
        return self._process.GetExitCodeProcess(self._pi[0])

    def wait_tree(self, timeout=5):
        deadline = time.monotonic()+timeout
        while self._job.QueryInformationJobObject(
                self._handle, self._job.JobObjectBasicAccountingInformation)["ActiveProcesses"]:
            if time.monotonic()>=deadline:
                raise OSError("Owned browser job cleanup did not settle")
            time.sleep(.02)


def _run_owned_browser(command, *, env, cwd=ROOT, timeout=110):
    if os.name != "nt":
        raise OSError("Browser containment is verified for Windows only")
    job = _WindowsBrowserJob()
    try:
        process = job.run(command, env=env, cwd=cwd)
        deadline = time.monotonic() + timeout
        while True:
            if time.monotonic() >= deadline:
                job.terminate()
                job.wait_tree()
                raise subprocess.TimeoutExpired(command, timeout)
            status = job.wait(100)
            if status == 0:
                code = job.exit_code()
                job.terminate()  # close descendants before releasing the job handle
                job.wait_tree()
                output = job.output()
                return subprocess.CompletedProcess(command, code, output, "")
    finally:
        job.close()


def prepare_manifest():
    """Fresh controlled build, stable reviewed sources, then private artifact."""
    before = {name: acceptance._sha256_file(ROOT / name) for name in required_pin_paths()}
    node = shutil.which("node")
    if not node:
        raise ValueError("Build runtime unavailable.")
    result = subprocess.run([node, str(ROOT / "apps/web/node_modules/next/dist/bin/next"), "build"],
        cwd=ROOT / "apps/web", env=web_environment(), stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    if result.returncode != 0:
        raise ValueError("Controlled web build failed.")
    document = make_manifest()
    if document["source_pins"] != before:
        raise ValueError("Sources changed during controlled build.")
    runtime = acceptance._runtime_directory(acceptance.APPROVED_RUNTIME_DIR)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = runtime / f"P5_APPROVED_MANIFEST_{stamp}.json"
    acceptance._write_json_exclusive(target, document)
    return {"status": "BUILD_VERIFIED", "manifest_path": str(target),
            "manifest_sha256": acceptance.canonical_json_sha256(document),
            "source_pin_count": len(before), "compiled_file_count": len(document["compiled_web"])}


def create_demo_app(engine, settings):
    from fastapi import FastAPI
    from app.mobility.catalog_repo import CatalogRepo
    from app.mobility.router import install_mobility
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    install_mobility(app, catalog=CatalogRepo(engine), enabled=True,
                     open_settings=settings, demo_geocode_enabled=True)
    return app


def _server_key():
    from dotenv import dotenv_values
    from pydantic import SecretStr
    # Read only the existing ignored backend configuration; never copy its bytes.
    key = os.environ.get("MOBILITY_ORS_API_KEY")
    if not key:
        for path in (ROOT / ".env", ROOT / "apps/api/.env"):
            if path.is_file():
                values = dotenv_values(path)
                key = values.get("MOBILITY_ORS_API_KEY")
                if key:
                    break
    if not key:
        if not sys.stdin.isatty():
            raise ValueError("Backend provider credential unavailable.")
        key = getpass.getpass("ORS key (hidden): ")
    if not key or any(char in key for char in "\r\n"):
        raise ValueError("Backend provider credential unavailable.")
    return SecretStr(key)


def _write_failure_report(error_type: str):
    try:
        runtime = acceptance._runtime_directory(acceptance.APPROVED_RUNTIME_DIR)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = runtime / f"P5_LIVE_{stamp}.json"
        acceptance._write_json_exclusive(path, {
            "status": "NOT_VERIFIED", "error_type": error_type,
            "provider_stats": "UNKNOWN",
        })
        return True
    except Exception:
        # Never replace the primary bounded failure with raw cleanup/IO details.
        return False


def run_pilot(manifest_path: Path, manifest_digest: str):
    try:
        return _run_pilot_impl(manifest_path, manifest_digest)
    except Exception as error:
        written = _write_failure_report(type(error).__name__)
        return {"status": "NOT_VERIFIED", "error_type": type(error).__name__,
                "receipt_status": "WRITTEN" if written else "REPORT_WRITE_FAILED"}


def _run_pilot_impl(manifest_path: Path, manifest_digest: str):
    import httpx
    import uvicorn
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(document, manifest_digest)
    runtime = acceptance._runtime_directory(acceptance.APPROVED_RUNTIME_DIR)
    acceptance._verify_receipt(runtime)  # Same current candidate P4, before traffic.
    config, _ = acceptance._load_runtime_config(runtime)
    acceptance._inspect_clone_identity(config)
    engine = acceptance.connect_readonly(config)
    web = server = thread = settings = None
    report = {"status": "NOT_VERIFIED", "manifest_sha256": manifest_digest}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = runtime / f"P5_LIVE_{stamp}.json"
    screenshot = runtime / f"P5_LIVE_{stamp}.png"
    try:
        before = acceptance._hash_public_tables(engine, acceptance._pinned_public_table_names())
        view_before = acceptance._hash_catalog_view(engine)
        if view_before["row_count"] != 789:
            raise ValueError("Catalog is not ready.")
        for port in (8033, 3033):
            acceptance._assert_port_free("127.0.0.1", port)
        settings = build_demo_live_settings(enabled=True, live_enabled=True, ors_api_key=_server_key())
        app = create_demo_app(engine, settings)
        # One Server object in this process, one event loop, no reload/workers.
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8033,
            log_level="critical", access_log=False, server_header=False,
            limit_concurrency=20, timeout_graceful_shutdown=3))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 15
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(.1)
        if not server.started:
            raise ValueError("Demo backend not ready.")
        node = shutil.which("node")
        if not node:
            raise ValueError("Browser runtime not ready.")
        web = acceptance._start_owned_process(
            [node, str(ROOT / "apps/web/node_modules/next/dist/bin/next"), "start",
             "--hostname", "127.0.0.1", "--port", "3033"],
            cwd=ROOT / "apps/web", env=web_environment())
        acceptance._wait_for_local_http(web, UI_ORIGIN + "/map", timeout_seconds=30)
        # Recheck all code/config bindings immediately before the first provider call.
        validate_manifest(document, manifest_digest)
        with httpx.Client(timeout=20, trust_env=False, follow_redirects=False) as client:
            rows = client.get(API_ORIGIN + "/mobility/listings?size=100").json()
            if rows["total"] != 789:
                raise ValueError("Demo catalog not ready.")
            listing = next(row for row in rows["items"] if row["position"] is not None)
            query = {"address": "Can Tho University", "bounds": {
                "south": 9.8, "west": 105.4, "north": 10.3, "east": 106.0}}
            geo1 = client.post(API_ORIGIN + "/mobility/geocode", json=query).json()
            geo2 = (client.post(API_ORIGIN + "/mobility/geocode", json=query).json()
                    if geo1["status"] in {"OK", "NO_MATCH", "AMBIGUOUS"} else None)
            report["geocode"] = {
                "status": geo1["status"], "repeat_status": None if geo2 is None else geo2["status"],
                "same_observation": geo1 == geo2,
                "evidence_kind": geo1["evidence_kind"], "queried_at": geo1["queried_at"],
                "candidate_count": geo1["candidate_count"],
            }
        browser = _run_owned_browser([node, str(ROOT / "scripts/open_mobility_tile_pilot.cjs"),
            str(listing["id"]), str(screenshot)], cwd=ROOT,
            env=web_environment(), timeout=110)
        try:
            report["browser"] = json.loads(browser.stdout)
        except (ValueError, TypeError):
            report["browser"] = {"status": "NOT_VERIFIED"}
        stats = settings.request_policy_gate.observation_stats()
        report["provider_stats"] = stats
        attempts = stats["backend_attempts"]
        report["data_unchanged"] = (
            before == acceptance._hash_public_tables(engine, acceptance._pinned_public_table_names())
            and view_before == acceptance._hash_catalog_view(engine))
        validate_manifest(document, manifest_digest)
        acceptance._verify_receipt(runtime)
        report["source_and_build_unchanged"] = True
        geo_pass = (geo1["status"] in {"OK", "NO_MATCH", "AMBIGUOUS"}
            and geo1["evidence_kind"] == "LIVE" and geo1 == geo2
            and attempts.get("nominatim") == 1 and stats["cache_hits"] == 1)
        if (geo_pass and browser.returncode == 0 and report["browser"]["status"] == "PASS"
                and attempts.get("ors") == 2 and attempts.get("osm_overpass") == 1
                and report["data_unchanged"]):
            report["status"] = "LIVE_API_UI_VERIFIED"
    except Exception as error:
        report["status"] = "NOT_VERIFIED"
        report["error_type"] = type(error).__name__
    finally:
        cleanup_errors = []
        if settings is not None:
            try: report["provider_stats"] = settings.request_policy_gate.observation_stats()
            except Exception:
                report["provider_stats"] = "UNKNOWN"
                cleanup_errors.append("ProviderStatsUnavailable")
        try:
            if server is not None: server.should_exit = True
            if thread is not None:
                thread.join(timeout=6)
                if thread.is_alive(): cleanup_errors.append("BackendStillRunning")
        except Exception as error: cleanup_errors.append(type(error).__name__)
        for cleanup in (lambda: acceptance._stop_owned_process(web), engine.dispose):
            try: cleanup()
            except Exception as error: cleanup_errors.append(type(error).__name__)
        if cleanup_errors:
            report["status"] = "NOT_VERIFIED"
            report["cleanup_errors"] = cleanup_errors
    acceptance._write_json_exclusive(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["manifest", "run"])
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--manifest-sha256", default="")
    args = parser.parse_args()
    try:
        if args.command == "manifest":
            print(json.dumps(prepare_manifest(), sort_keys=True))
            return 0
        report = run_pilot(args.manifest, args.manifest_sha256)
        print(json.dumps(report, sort_keys=True))
        return 0 if report["status"] == "LIVE_API_UI_VERIFIED" else 1
    except Exception as error:
        # Native exceptions may contain credentials, URLs or provider bodies.
        print(json.dumps({"status": "NOT_VERIFIED", "error_type": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
