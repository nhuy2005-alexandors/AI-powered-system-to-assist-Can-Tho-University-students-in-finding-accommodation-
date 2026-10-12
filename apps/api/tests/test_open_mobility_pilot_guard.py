"""Pilot preflight is testable offline; no infrastructure or provider access."""
import copy
import importlib
from pathlib import Path

import pytest


def pilot():
    return importlib.import_module("scripts.open_mobility_pilot")


@pytest.mark.parametrize("legacy_location", ["environment", "dotenv"])
def test_server_key_never_reuses_legacy_ors_credential(monkeypatch, tmp_path, legacy_location):
    p = pilot()
    monkeypatch.setattr(p, "ROOT", tmp_path)
    monkeypatch.setattr(p.sys.stdin, "isatty", lambda: False)
    monkeypatch.delenv("MOBILITY_ORS_API_KEY", raising=False)
    monkeypatch.delenv("ORS_API_KEY", raising=False)
    if legacy_location == "environment":
        monkeypatch.setenv("ORS_API_KEY", "synthetic-legacy-only")
    else:
        (tmp_path / ".env").write_text("ORS_API_KEY=synthetic-legacy-only\n")
    with pytest.raises(ValueError, match="Backend provider credential unavailable"):
        p._server_key()


def test_server_key_accepts_separate_mobility_credential(monkeypatch, tmp_path):
    p = pilot()
    monkeypatch.setattr(p, "ROOT", tmp_path)
    monkeypatch.setenv("MOBILITY_ORS_API_KEY", "synthetic-mobility-only")
    monkeypatch.setenv("ORS_API_KEY", "synthetic-legacy-only")
    result = p._server_key()
    assert result.get_secret_value() == "synthetic-mobility-only"
    assert "synthetic-mobility-only" not in repr(result)


def test_manifest_requires_independent_digest_complete_inventory_and_unchanged_bytes(tmp_path):
    p = pilot()
    paths = p.required_pin_paths()
    for name in set(paths) | set(p.acceptance.PUBLIC_ARTIFACTS):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"synthetic pinned bytes")
    for name in ("BUILD_ID", "server/app/map/page.js", "static/chunks/synthetic.js"):
        target = tmp_path / "apps/web/.next" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"synthetic build bytes")
    document = p.make_manifest(root=tmp_path)
    digest = p.acceptance.canonical_json_sha256(document)
    p.validate_manifest(document, digest, root=tmp_path)
    assert document["compiled_web"]["BUILD_ID"]
    build = tmp_path / "apps/web/.next/static/chunks/synthetic.js"
    build.write_bytes(b"stale or replaced compiled code")
    with pytest.raises(ValueError):
        p.validate_manifest(document, digest, root=tmp_path)
    build.write_bytes(b"synthetic build bytes")
    for mutate in ("digest", "omit", "budget", "endpoint"):
        changed = copy.deepcopy(document)
        expected = digest
        if mutate == "digest":
            expected = "0" * 64
        elif mutate == "omit":
            changed["source_pins"].pop("scripts/open_mobility_tile_pilot.cjs")
            expected = p.acceptance.canonical_json_sha256(changed)
        elif mutate == "budget":
            changed["budget"]["tiles"] = 61
            expected = p.acceptance.canonical_json_sha256(changed)
        else:
            changed["endpoints"]["nominatim"] = "https://unapproved.test"
            expected = p.acceptance.canonical_json_sha256(changed)
        with pytest.raises(ValueError):
            p.validate_manifest(changed, expected, root=tmp_path)
    (tmp_path / "scripts/open_mobility_tile_pilot.cjs").write_bytes(b"changed runner")
    with pytest.raises(ValueError):
        p.validate_manifest(document, digest, root=tmp_path)


def test_frontend_environment_never_inherits_provider_secret_or_dsn(monkeypatch):
    p = pilot()
    monkeypatch.setenv("MOBILITY_ORS_API_KEY", "synthetic-secret")
    monkeypatch.setenv("DATABASE_URL", "synthetic-dsn")
    monkeypatch.setenv("NEXT_PUBLIC_API_URL", "https://unapproved.test")
    env = p.web_environment()
    assert "synthetic-secret" not in repr(env)
    assert "synthetic-dsn" not in repr(env)
    assert env["API_INTERNAL_URL"] == "http://127.0.0.1:8033"
    assert "NEXT_PUBLIC_API_URL" not in env
    assert env["MOBILITY_TILES_ENABLED"] == "true"


def test_single_worker_app_opts_into_demo_only_geocode_without_importing_production():
    from fastapi.testclient import TestClient
    from app.mobility.providers.open_config import OpenMobilitySettings
    p = pilot()
    app = p.create_demo_app(object(), OpenMobilitySettings())
    client = TestClient(app)
    assert client.post("/crawler/run").status_code == 404
    assert client.post("/auth/login").status_code == 404
    assert client.post("/mobility/geocode", json={
        "address": "Synthetic public landmark", "bounds": {
            "south": 9.9, "west": 105.5, "north": 10.2, "east": 105.9,
        },
    }).json()["status"] == "NOT_CONFIGURED"


@pytest.mark.parametrize("failure", [None, "timeout", "assign", "resume"])
def test_browser_child_contained_before_resume_and_job_closed_on_all_paths(monkeypatch, failure):
    p = pilot()
    events = []

    class Job:
        def __init__(self): events.append("job_create")
        def run(self, command, *, env, cwd):
            events.append("spawn_suspended")
            if failure == "assign": events.append("assign"); raise OSError("synthetic private error")
            events.append("assign")
            if failure == "resume": events.append("resume"); raise OSError("synthetic private error")
            events.append("resume")
            return (12345, 12346)
        def close(self): events.append("job_close")
        def terminate(self): events.append("job_terminate")
        def output(self): return '{"status":"NOT_VERIFIED"}'
        def wait(self, timeout_ms): return 0 if failure != "timeout" else 258
        def exit_code(self): return 0
        def wait_tree(self, timeout=5): events.append("tree_reaped")

    monkeypatch.setattr(p, "_WindowsBrowserJob", Job, raising=False)
    monkeypatch.setattr(p.os, "name", "nt")
    ticks = iter([0, 999] if failure == "timeout" else [0] * 8)
    monkeypatch.setattr(p.time, "monotonic", lambda: next(ticks, 999 if failure == "timeout" else 0))
    if failure:
        with pytest.raises((OSError, p.subprocess.TimeoutExpired)):
            p._run_owned_browser(["synthetic-child"], env={"SYNTHETIC": "safe"}, timeout=0.01)
    else:
        result = p._run_owned_browser(["synthetic-child"], env={"SYNTHETIC": "safe"})
        assert result.returncode == 0
    assert events[:3] == ["job_create", "spawn_suspended", "assign"]
    assert events.count("job_close") == 1
    if failure == "assign": assert "resume" not in events
    if failure == "timeout": assert "job_terminate" in events


@pytest.mark.parametrize("cleanup_failure", [False, True])
def test_runtime_error_still_writes_redacted_failure_receipt_and_disposes_engine(monkeypatch, tmp_path, cleanup_failure):
    p = pilot()
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    events, receipts = [], []
    class Engine:
        def dispose(self): events.append("dispose")
    monkeypatch.setattr(p, "validate_manifest", lambda *args, **kwargs: None)
    monkeypatch.setattr(p.acceptance, "_runtime_directory", lambda *args: tmp_path)
    monkeypatch.setattr(p.acceptance, "_verify_receipt", lambda *args: None)
    monkeypatch.setattr(p.acceptance, "_load_runtime_config", lambda *args: (None, b""))
    monkeypatch.setattr(p.acceptance, "_inspect_clone_identity", lambda *args: None)
    monkeypatch.setattr(p.acceptance, "connect_readonly", lambda *args: Engine())
    monkeypatch.setattr(p.acceptance, "_pinned_public_table_names", lambda: ())
    def fail(*args): raise OSError("synthetic-private-credential-must-not-leak")
    monkeypatch.setattr(p.acceptance, "_hash_public_tables", fail)
    def stop(*args):
        events.append("stop_web")
        if cleanup_failure: raise OSError("synthetic-private-cleanup")
    monkeypatch.setattr(p.acceptance, "_stop_owned_process", stop)
    monkeypatch.setattr(p.acceptance, "_write_json_exclusive", lambda path, report: receipts.append(report.copy()))
    report = p.run_pilot(manifest, "0" * 64)
    assert report["status"] == "NOT_VERIFIED"
    assert report["error_type"] == "OSError"
    assert receipts == [report]
    assert events == ["stop_web", "dispose"]
    assert "synthetic-private" not in repr(report)
    if cleanup_failure: assert report["cleanup_errors"] == ["OSError"]


def test_preflight_failure_is_redacted_and_persists_not_verified(monkeypatch):
    p = pilot()
    receipts = []
    monkeypatch.setattr(p.acceptance, "_runtime_directory", lambda *args: Path("C:/private-runtime"))
    monkeypatch.setattr(p.acceptance, "_verify_receipt", lambda *args: (_ for _ in ()).throw(OSError("secret")))
    monkeypatch.setattr(p.acceptance, "_write_json_exclusive", lambda path, report: receipts.append(report))
    report = p.run_pilot(Path("bad"), "0" * 64)
    assert report == {"status": "NOT_VERIFIED", "error_type": "FileNotFoundError", "receipt_status": "WRITTEN"}
    assert receipts and receipts[-1]["status"] == "NOT_VERIFIED"
    assert "secret" not in repr(receipts[-1])


def test_report_write_failure_is_explicit(monkeypatch):
    p = pilot()
    monkeypatch.setattr(p.acceptance, "_runtime_directory", lambda *args: Path("C:/private-runtime"))
    monkeypatch.setattr(p.acceptance, "_write_json_exclusive", lambda *args: (_ for _ in ()).throw(OSError("io")))
    report = p.run_pilot(Path("bad"), "0" * 64)
    assert report["receipt_status"] == "REPORT_WRITE_FAILED"
    assert "secret" not in repr(report)


@pytest.mark.parametrize("stats_failure", [True, False])
def test_final_provider_stats_failure_cannot_leave_live_pass(monkeypatch, tmp_path, stats_failure):
    import json
    from types import SimpleNamespace
    import httpx, uvicorn
    p = pilot()
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(p, "validate_manifest", lambda *a, **k: None)
    for name in ("_verify_receipt", "_inspect_clone_identity", "_assert_port_free", "_wait_for_local_http", "_stop_owned_process"):
        monkeypatch.setattr(p.acceptance, name, lambda *a, **k: None)
    monkeypatch.setattr(p.acceptance, "_runtime_directory", lambda *a: tmp_path)
    monkeypatch.setattr(p.acceptance, "_load_runtime_config", lambda *a: (None,b""))
    monkeypatch.setattr(p.acceptance, "connect_readonly", lambda *a: SimpleNamespace(dispose=lambda:None))
    monkeypatch.setattr(p.acceptance, "_pinned_public_table_names", lambda: ())
    monkeypatch.setattr(p.acceptance, "_hash_public_tables", lambda *a: {})
    monkeypatch.setattr(p.acceptance, "_hash_catalog_view", lambda *a: {"row_count":789})
    monkeypatch.setattr(p.acceptance, "_start_owned_process", lambda *a, **k: object())
    receipts = []
    monkeypatch.setattr(p.acceptance, "_write_json_exclusive", lambda path, report: receipts.append(copy.deepcopy(report)))
    calls = []
    def stats():
        calls.append(1)
        if stats_failure and len(calls)>1: raise OSError("synthetic-private-stats-error")
        return {"backend_attempts":{"nominatim":1,"ors":2,"osm_overpass":1},"cache_hits":1,
                "provider_failures":{"osm_overpass":{"HTTP_NON_200":1}} if not stats_failure else {}}
    settings = SimpleNamespace(request_policy_gate=SimpleNamespace(observation_stats=stats))
    monkeypatch.setattr(p, "build_demo_live_settings", lambda **k: settings)
    monkeypatch.setattr(p, "_server_key", lambda: "synthetic")
    monkeypatch.setattr(p, "create_demo_app", lambda *a: object())
    monkeypatch.setattr(uvicorn, "Server", lambda *a: SimpleNamespace(started=True,run=lambda:None,should_exit=False))
    class Client:
        def __init__(self, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def get(self, *a): return SimpleNamespace(json=lambda:{"total":789,"items":[{"id":123,"position":{}}]})
        def post(self, *a, **k): return SimpleNamespace(json=lambda:{"status":"OK","evidence_kind":"LIVE","queried_at":"synthetic-time","candidate_count":1})
    monkeypatch.setattr(httpx, "Client", Client)
    monkeypatch.setattr(p, "_run_owned_browser", lambda *a, **k: p.subprocess.CompletedProcess(
        [], 0 if stats_failure else 1, json.dumps({"status":"PASS" if stats_failure else "NOT_VERIFIED"}), ""))
    report = p.run_pilot(manifest, "0"*64)
    assert len(calls)==2, "must reach the final stats read after all PASS predicates"
    assert report["status"] == "NOT_VERIFIED"
    if stats_failure:
        assert report["provider_stats"] == "UNKNOWN"
        assert report["cleanup_errors"] == ["ProviderStatsUnavailable"]
    else:
        assert report["provider_stats"]["provider_failures"] == {"osm_overpass":{"HTTP_NON_200":1}}
        assert "cleanup_errors" not in report
    assert receipts == [report]
    assert "synthetic-private" not in repr(report)


def test_windows_job_limit_mapping_is_set_before_process_assignment(monkeypatch):
    p = pilot()
    if p.os.name != "nt":
        pytest.skip("Windows Job Object API")
    import win32job, win32api
    events = []
    monkeypatch.setattr(win32job, "CreateJobObject", lambda *_: events.append("create") or 7)
    monkeypatch.setattr(win32job, "QueryInformationJobObject", lambda *_: {"BasicLimitInformation":{"LimitFlags":0}})
    monkeypatch.setattr(win32job, "SetInformationJobObject", lambda *_: events.append("set"))
    monkeypatch.setattr(win32job, "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE", 0x2000, raising=False)
    monkeypatch.setattr(win32api, "CloseHandle", lambda *_: events.append("close"))
    monkeypatch.setattr(p, "_WindowsBrowserJob", p._WindowsBrowserJob)
    job = p._WindowsBrowserJob()
    assert events == ["create", "set"]
    job.close()


def test_native_windows_job_can_run_and_reap_no_network_child():
    p = pilot()
    if p.os.name != "nt":
        pytest.skip("Windows Job Object API")
    result = p._run_owned_browser([p.sys.executable, "-c", "print('SAFE_CHILD')"],
                                  env=p.web_environment(), timeout=5)
    assert result.returncode == 0
    assert result.stdout.strip() == "SAFE_CHILD"


def test_native_assign_failure_reaps_suspended_process_without_execution(monkeypatch):
    p = pilot()
    if p.os.name != "nt": pytest.skip("Windows Job Object API")
    import win32api, win32event, win32job, win32process
    process_handles = []
    create = win32process.CreateProcess
    def capture(*args, **kwargs):
        pi = create(*args, **kwargs)
        process_handles.append(win32api.OpenProcess(0x100000 | 1, False, pi[2]))
        return pi
    monkeypatch.setattr(win32process, "CreateProcess", capture)
    monkeypatch.setattr(win32job, "AssignProcessToJobObject", lambda *a: (_ for _ in ()).throw(OSError("synthetic-assign-denied")))
    try:
        with pytest.raises(OSError, match="synthetic-assign-denied"):
            p._run_owned_browser([p.sys.executable,"-c","print('MUST_NOT_RUN')"],env=p.web_environment(),timeout=2)
        assert len(process_handles)==1
        assert win32event.WaitForSingleObject(process_handles[0], 0)==0
    finally:
        for handle in process_handles:
            if win32event.WaitForSingleObject(handle, 0)!=0:
                win32api.TerminateProcess(handle,1)
            win32api.CloseHandle(handle)


def test_unassigned_termination_failure_cannot_claim_cleanup(monkeypatch):
    p = pilot()
    if p.os.name != "nt": pytest.skip("Windows Job Object API")
    import win32event
    from types import SimpleNamespace
    events=[]
    job=object.__new__(p._WindowsBrowserJob)
    job._pi=(7,8,123,124);job._assigned=False;job._handle=9;job._output_path=None
    job._process=SimpleNamespace(TerminateProcess=lambda *a:(_ for _ in ()).throw(OSError("synthetic-terminate-denied")))
    job._api=SimpleNamespace(CloseHandle=lambda handle:events.append(handle))
    monkeypatch.setattr(win32event,"WaitForSingleObject",lambda *a:258)
    with pytest.raises(OSError,match="cleanup not verified"): job.close()
    assert events==[7,8,9]


@pytest.mark.parametrize("parent_exit", [False, True])
def test_native_windows_job_terminates_grandchild_on_timeout_and_parent_exit(tmp_path, parent_exit):
    p = pilot()
    if p.os.name != "nt": pytest.skip("Windows Job Object API")
    import win32api, win32event
    pid_file = tmp_path / "owned-grandchild.pid"
    code = (
        "import subprocess,sys,time; from pathlib import Path; "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
        "Path(sys.argv[1]).write_text(str(child.pid)); "
        + ("print('SAFE_PARENT_EXIT')" if parent_exit else "time.sleep(60)")
    )
    try:
        if parent_exit:
            result = p._run_owned_browser([p.sys.executable, "-c", code, str(pid_file)],
                                         env=p.web_environment(), timeout=5)
            assert result.returncode == 0
        else:
            with pytest.raises(p.subprocess.TimeoutExpired):
                p._run_owned_browser([p.sys.executable, "-c", code, str(pid_file)],
                                     env=p.web_environment(), timeout=2)
        assert pid_file.exists(), "counterexample must actually spawn its grandchild"
        pid = int(pid_file.read_text())
        try: handle = win32api.OpenProcess(0x100000 | 1, False, pid)
        except Exception as error:
            assert getattr(error, "winerror", None) == 87
        else:
            try:
                assert win32event.WaitForSingleObject(handle, 5000) == 0, "owned grandchild leaked"
            finally:
                if win32event.WaitForSingleObject(handle, 0) != 0:
                    win32api.TerminateProcess(handle, 1)
                win32api.CloseHandle(handle)
    finally:
        # Failure cleanup is exact to the PID produced by this owned canary.
        if pid_file.exists():
            try:
                handle = win32api.OpenProcess(0x100000 | 1, False, int(pid_file.read_text()))
                if win32event.WaitForSingleObject(handle, 0) != 0:
                    win32api.TerminateProcess(handle, 1)
                win32api.CloseHandle(handle)
            except Exception: pass
