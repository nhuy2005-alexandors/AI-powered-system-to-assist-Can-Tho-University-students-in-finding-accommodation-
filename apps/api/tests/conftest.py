import os
import sys
from pathlib import Path
import socket
import threading
import unittest.mock

# cho phép `import app...` khi chạy pytest từ apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

try:
    from tests.ugc_harness import (
        validate_ugc_engine_target,
        validate_ugc_psycopg_connect_args,
    )
except ImportError:
    try:
        from apps.api.tests.ugc_harness import (  # type: ignore
            validate_ugc_engine_target,
            validate_ugc_psycopg_connect_args,
        )
    except ImportError:
        # Keep this conftest importable in minimal environments. If a DB
        # connection is opted in without the validator, fail closed below.
        validate_ugc_engine_target = None
        validate_ugc_psycopg_connect_args = None

try:
    import httpx
    _orig_client_send = httpx.Client.send
    _orig_async_client_send = httpx.AsyncClient.send
except ImportError:
    httpx = None
    _orig_client_send = None
    _orig_async_client_send = None

try:
    import psycopg
    _orig_psycopg_connect = psycopg.connect
    _orig_psycopg_async_connect = getattr(getattr(psycopg, "AsyncConnection", None), "connect", None)
except ImportError:
    psycopg = None
    _orig_psycopg_connect = None
    _orig_psycopg_async_connect = None

try:
    import sqlalchemy
    import sqlalchemy.engine
    _orig_engine_connect = sqlalchemy.engine.Engine.connect
    _orig_engine_raw_connection = getattr(sqlalchemy.engine.Engine, "raw_connection", None)
except ImportError:
    sqlalchemy = None
    _orig_engine_connect = None
    _orig_engine_raw_connection = None

try:
    import starlette.testclient
    _starlette_testclient_transport = getattr(starlette.testclient, "_TestClientTransport", None)
except (ImportError, Exception):
    _starlette_testclient_transport = None

FIXTURES = Path(__file__).parent / "fixtures"

_orig_socket_connect = socket.socket.connect
_orig_socket_connect_ex = socket.socket.connect_ex
_orig_socketpair = getattr(socket, "socketpair", None)
_tls = threading.local()

FORBIDDEN_SERVICE_PORTS = {5432, 6379, 8000, 3000}
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
ALLOWED_MOCK_TRANSPORTS = set()


def register_mock_transport(transport_cls):
    """Đăng ký custom mock transport hợp lệ cho môi trường test."""
    ALLOWED_MOCK_TRANSPORTS.add(transport_cls)


def pytest_addoption(parser):
    parser.addoption(
        "--require-test-db",
        action="store_true",
        default=False,
        help="Fail integration DB tests if test DB is unavailable instead of skipping",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "allow_db: opt-in marker to allow database connections for integration tests"
    )


def pytest_runtest_setup(item):
    if item.get_closest_marker("allow_db"):
        require_db = False
        if hasattr(item, "config") and hasattr(item.config, "getoption"):
            opt = item.config.getoption("--require-test-db", False)
            if not isinstance(opt, unittest.mock.Mock):
                require_db = bool(opt)
        if require_db:
            if os.environ.get("TEST_DB_ALLOW") != "1":
                pytest.fail("Test DB is required (--require-test-db was specified) but TEST_DB_ALLOW is not '1'")
            if not os.environ.get("TEST_DATABASE_URL"):
                pytest.fail("Test DB is required (--require-test-db was specified) but TEST_DATABASE_URL is not set")
        elif os.environ.get("TEST_DB_ALLOW") != "1":
            pytest.skip("Integration DB test skipped: requires TEST_DB_ALLOW=1")


@pytest.fixture
def allow_db(request: pytest.FixtureRequest = None) -> bool:
    """Opt-in fixture for integration tests requiring real DB access."""
    require_db = False
    if request is not None and hasattr(request, "config") and hasattr(request.config, "getoption"):
        opt = request.config.getoption("--require-test-db", False)
        if not isinstance(opt, unittest.mock.Mock):
            require_db = bool(opt)
    if require_db:
        if os.environ.get("TEST_DB_ALLOW") != "1":
            pytest.fail("Test DB is required (--require-test-db was specified) but TEST_DB_ALLOW is not '1'")
        if not os.environ.get("TEST_DATABASE_URL"):
            pytest.fail("Test DB is required (--require-test-db was specified) but TEST_DATABASE_URL is not set")
    elif os.environ.get("TEST_DB_ALLOW") != "1":
        pytest.skip("Integration DB test skipped: requires TEST_DB_ALLOW=1")
    return True


def _get_allowed_test_db_endpoint():
    env_host = os.environ.get("TEST_DB_HOST", "").strip().lower()
    allowed_hosts = {env_host} if env_host else {"127.0.0.1", "localhost", "::1"}

    env_port = os.environ.get("TEST_DB_PORT", "5433").strip()
    try:
        allowed_port = int(env_port)
    except (ValueError, TypeError):
        allowed_port = 5433
    return allowed_hosts, allowed_port


def _check_socket_address(sock, address, allow_db: bool = False) -> None:
    if not isinstance(address, (tuple, list)) or len(address) < 2:
        raise RuntimeError(
            "Network/DB access is strictly prohibited in offline test: invalid address format"
        )

    host = address[0]
    port = address[1]
    try:
        port_num = int(port)
    except (ValueError, TypeError):
        raise RuntimeError(
            f"Invalid port {port!r} blocked in offline test: {address}"
        )

    norm_host = str(host).strip().lower()

    # 1. Cấm tuyệt đối cổng 5432 (DB ứng dụng mặc định) trong mọi trường hợp
    if port_num == 5432:
        raise RuntimeError(
            f"Application database port 5432 is strictly blocked in tests: attempted connect to ({norm_host}, {port_num})"
        )

    # 2. Endpoint DB test được phép khi và chỉ khi có opt-in allow_db
    if allow_db:
        allowed_hosts, allowed_port = _get_allowed_test_db_endpoint()
        if allowed_port != 5432 and port_num == allowed_port and norm_host in allowed_hosts:
            return

    # 3. Chặn các cổng dịch vụ khác: 6379 (Redis), 8000 (API), 3000 (Web)
    if port_num in FORBIDDEN_SERVICE_PORTS:
        raise RuntimeError(
            f"Service port {port_num} is strictly blocked in offline test: attempted connect to ({norm_host}, {port_num})"
        )

    # 4. Chặn toàn bộ IP / host ngoài loopback
    if norm_host not in LOOPBACK_HOSTS:
        raise RuntimeError(
            f"External network access is strictly prohibited in offline test: attempted connect to ({norm_host}, {port_num})"
        )

    # 5. Cấm cổng hệ thống/privileged (< 1024)
    if port_num < 1024:
        raise RuntimeError(
            f"Privileged port {port_num} on loopback is blocked in offline test: attempted connect to ({norm_host}, {port_num})"
        )

    # 6. Chặn mọi kết nối loopback không thuộc socketpair nội bộ (Windows ProactorEventLoop)
    if not getattr(_tls, "in_internal_socketpair", False):
        raise RuntimeError(
            f"Non-internal loopback socket connection is blocked in offline test: attempted connect to ({norm_host}, {port_num})"
        )

    # 7. Socket family của socket nội bộ phải là AF_INET hoặc AF_INET6
    sock_family = getattr(sock, "family", None)
    if sock_family not in (socket.AF_INET, socket.AF_INET6):
        raise RuntimeError(
            f"Non-IP socket family {sock_family} blocked in offline test: attempted connect to ({norm_host}, {port_num})"
        )


def _is_mocked_http_transport(transport) -> bool:
    if transport is None:
        return False
    if isinstance(transport, (httpx.HTTPTransport, httpx.AsyncHTTPTransport)):
        return False
    if isinstance(transport, httpx.MockTransport):
        return True
    if hasattr(httpx, "ASGITransport") and isinstance(transport, httpx.ASGITransport):
        return True
    if hasattr(httpx, "WSGITransport") and isinstance(transport, httpx.WSGITransport):
        return True
    if _starlette_testclient_transport is not None and isinstance(
        transport, _starlette_testclient_transport
    ):
        return True
    if isinstance(transport, (unittest.mock.NonCallableMock, unittest.mock.Mock)):
        return True
    if hasattr(transport, "_mock_return_value") or hasattr(transport, "_mock_wraps"):
        return True
    if type(transport) in ALLOWED_MOCK_TRANSPORTS or any(
        isinstance(transport, cls) for cls in ALLOWED_MOCK_TRANSPORTS
    ):
        return True
    return False


@pytest.fixture(autouse=True)
def guard_no_external_network_or_db(request: pytest.FixtureRequest, monkeypatch):
    """Bảo đảm 100% test offline: chặn mọi socket kết nối ra ngoài hoặc DB thật.

    Chỉ cho phép:
    1. Socketpair nội bộ Windows ProactorEventLoop (ephemeral loopback).
    2. Endpoint DB test được chỉ định (TEST_DB_HOST, TEST_DB_PORT) KHI VÀ CHỈ KHI
       có opt-in TEST_DB_ALLOW=1 cùng marker hoặc fixture allow_db (cấm tuyệt đối port 5432).
    """
    is_env_opted = os.environ.get("TEST_DB_ALLOW") == "1"
    has_marker = bool(request.node.get_closest_marker("allow_db"))
    has_fixture = "allow_db" in getattr(request, "fixturenames", ())
    allow_db_opted = is_env_opted and (has_marker or has_fixture)

    def _guarded_connect(self, address):
        _check_socket_address(self, address, allow_db=allow_db_opted)
        return _orig_socket_connect(self, address)

    def _guarded_connect_ex(self, address):
        _check_socket_address(self, address, allow_db=allow_db_opted)
        return _orig_socket_connect_ex(self, address)

    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _guarded_connect_ex)

    if _orig_socketpair is not None:
        def _guarded_socketpair(*args, **kwargs):
            _tls.in_internal_socketpair = True
            try:
                return _orig_socketpair(*args, **kwargs)
            finally:
                _tls.in_internal_socketpair = False

        monkeypatch.setattr(socket, "socketpair", _guarded_socketpair)

    if httpx is not None:
        def _guarded_client_send(self, request, *args, **kwargs):
            if not _is_mocked_http_transport(getattr(self, "_transport", None)):
                raise RuntimeError(
                    "Real network HTTP request blocked in offline test: httpx.Client must use MockTransport"
                )
            return _orig_client_send(self, request, *args, **kwargs)

        async def _guarded_async_client_send(self, request, *args, **kwargs):
            if not _is_mocked_http_transport(getattr(self, "_transport", None)):
                raise RuntimeError(
                    "Real network HTTP request blocked in offline test: httpx.AsyncClient must use MockTransport"
                )
            return await _orig_async_client_send(self, request, *args, **kwargs)

        monkeypatch.setattr(httpx.Client, "send", _guarded_client_send)
        monkeypatch.setattr(httpx.AsyncClient, "send", _guarded_async_client_send)

    if psycopg is not None:
        def _guarded_psycopg_connect(*args, **kwargs):
            if allow_db_opted and _orig_psycopg_connect is not None:
                if validate_ugc_psycopg_connect_args is None:
                    raise RuntimeError(
                        "Database connection blocked in tests: UGC target validator unavailable"
                    )
                validate_ugc_psycopg_connect_args(args, kwargs)
                return _orig_psycopg_connect(*args, **kwargs)
            raise RuntimeError(
                "Database connection blocked in offline test: attempted psycopg.connect"
            )

        monkeypatch.setattr(psycopg, "connect", _guarded_psycopg_connect)
        if hasattr(psycopg, "Connection"):
            monkeypatch.setattr(psycopg.Connection, "connect", _guarded_psycopg_connect)
        if hasattr(psycopg, "AsyncConnection"):
            async def _guarded_psycopg_async_connect(*args, **kwargs):
                if allow_db_opted and _orig_psycopg_async_connect is not None:
                    if validate_ugc_psycopg_connect_args is None:
                        raise RuntimeError(
                            "Database connection blocked in tests: UGC target validator unavailable"
                        )
                    validate_ugc_psycopg_connect_args(args, kwargs)
                    return await _orig_psycopg_async_connect(*args, **kwargs)
                raise RuntimeError(
                    "Database connection blocked in offline test: attempted psycopg.AsyncConnection.connect"
                )

            monkeypatch.setattr(psycopg.AsyncConnection, "connect", _guarded_psycopg_async_connect)

    if sqlalchemy is not None and hasattr(sqlalchemy, "engine"):
        def _guarded_engine_connect(self, *args, **kwargs):
            if allow_db_opted and _orig_engine_connect is not None:
                if validate_ugc_engine_target is None:
                    raise RuntimeError(
                        "Database connection blocked in tests: UGC target validator unavailable"
                    )
                validate_ugc_engine_target(self)
                return _orig_engine_connect(self, *args, **kwargs)
            if isinstance(self, (unittest.mock.NonCallableMock, unittest.mock.Mock)) or hasattr(self, "_mock_return_value"):
                if hasattr(self, "connect") and callable(self.connect) and self.connect is not _guarded_engine_connect:
                    return self.connect(*args, **kwargs)
                return self
            raise RuntimeError(
                "Database connection blocked in offline test: attempted sqlalchemy Engine.connect"
            )

        def _guarded_engine_raw_connection(self, *args, **kwargs):
            if allow_db_opted and _orig_engine_raw_connection is not None:
                if validate_ugc_engine_target is None:
                    raise RuntimeError(
                        "Database connection blocked in tests: UGC target validator unavailable"
                    )
                validate_ugc_engine_target(self)
                return _orig_engine_raw_connection(self, *args, **kwargs)
            if isinstance(self, (unittest.mock.NonCallableMock, unittest.mock.Mock)) or hasattr(self, "_mock_return_value"):
                return self
            raise RuntimeError(
                "Database connection blocked in offline test: attempted sqlalchemy Engine.raw_connection"
            )

        monkeypatch.setattr(sqlalchemy.engine.Engine, "connect", _guarded_engine_connect)
        if _orig_engine_raw_connection is not None:
            monkeypatch.setattr(sqlalchemy.engine.Engine, "raw_connection", _guarded_engine_raw_connection)


@pytest.fixture
def phongtro_html() -> str:
    return (FIXTURES / "phongtro123_list.html").read_text(encoding="utf-8")


@pytest.fixture
def phongtro_detail_html() -> str:
    return (FIXTURES / "phongtro123_detail.html").read_text(encoding="utf-8")


@pytest.fixture
def tromoi_html() -> str:
    return (FIXTURES / "tromoi_list.html").read_text(encoding="utf-8")


@pytest.fixture
def tromoi_detail_html() -> str:
    return (FIXTURES / "tromoi_detail.html").read_text(encoding="utf-8")


@pytest.fixture
def mogi_html() -> str:
    return (FIXTURES / "mogi_list.html").read_text(encoding="utf-8")


@pytest.fixture
def mogi_detail_html() -> str:
    return (FIXTURES / "mogi_detail.html").read_text(encoding="utf-8")
