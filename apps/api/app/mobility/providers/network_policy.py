"""Fail-closed, bounded transport shared by open mobility providers."""
import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import socket
from types import MappingProxyType
from typing import Literal, Mapping
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


ProviderName = Literal["ors", "osm_overpass", "nominatim"]
CachePolicy = Literal["NO_CACHE_ALLOWED", "MEMORY_24H"]
PolicyStatus = Literal[
    "NOT_CONFIGURED", "CAPABILITY_UNVERIFIED", "RATE_LIMITED", "PROVIDER_ERROR",
]
_OVERPASS_FAILURE_CODES = frozenset({
    "HTTP_NON_200", "RATE_LIMITED", "MALFORMED_RESPONSE",
    "POLICY_OR_TRANSPORT", "QUERY_INVALID",
})


class ProviderPolicy(BaseModel):
    """One content-bound endpoint permission record; never loaded from a request."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    provider: ProviderName
    base_url: str
    allowed_paths: tuple[str, ...] = Field(min_length=1)
    allowed_capabilities: tuple[str, ...] = Field(min_length=1)
    attribution: tuple[str, ...] = Field(min_length=1)
    user_agent: str | None = None
    cache_policy: CachePolicy = "NO_CACHE_ALLOWED"
    policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    approved_until: datetime
    max_requests: int = Field(ge=0)
    max_rps: float = Field(gt=0, le=1, allow_inf_nan=False)
    max_concurrency: Literal[1] = 1
    timeout_seconds: Literal[10.0] = 10.0
    connect_timeout_seconds: Literal[2.0] = 2.0
    max_response_bytes: Literal[1_048_576] = 1_048_576

    @field_validator("base_url")
    @classmethod
    def secure_base_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or
                parsed.query or parsed.fragment or parsed.path not in ("", "/")):
            raise ValueError("provider base URL must be an HTTPS origin")
        try:
            port = parsed.port
        except ValueError:
            raise ValueError("provider base URL has an invalid port") from None
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("provider base URL has an invalid port")
        try:
            literal = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            host = parsed.hostname.encode("idna").decode("ascii")
            if host.lower() != parsed.hostname.lower():
                raise ValueError("provider host must use its canonical ASCII name")
        else:
            if not literal.is_global:
                raise ValueError("provider base URL cannot target a private or reserved IP")
        return value

    @field_validator("allowed_paths")
    @classmethod
    def exact_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("allowed paths must be unique")
        for path in value:
            parsed = urlsplit(path)
            if (not path.startswith("/") or parsed.path != path or parsed.query or parsed.fragment or
                    "*" in path or "\\" in path or any(part in {".", ".."} for part in path.split("/"))):
                raise ValueError("allowed paths must be exact absolute paths")
        return value

    @field_validator("allowed_capabilities", "attribution")
    @classmethod
    def nonempty_unique_entries(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value) or any(not item.strip() for item in value):
            raise ValueError("policy entries must be unique and nonempty")
        return value

    @field_validator("user_agent")
    @classmethod
    def safe_user_agent(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or len(value) > 256 or "\r" in value or "\n" in value):
            raise ValueError("user agent is invalid")
        return value

    @field_validator("approved_until")
    @classmethod
    def approval_is_utc(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("approval expiry must include a UTC offset")
        return value.astimezone(timezone.utc)


def policy_digest(policy: ProviderPolicy) -> str:
    """Hash the exact validated policy record without its self-declared digest."""
    value = policy.model_dump(mode="json", exclude={"policy_sha256"})
    encoded = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ProviderResponse:
    status_code: int
    body: bytes
    observed_at: datetime
    evidence_kind: Literal["SYNTHETIC_FIXTURE", "LIVE"]


class RequestPolicyError(RuntimeError):
    """Safe typed denial; its public details contain only a frozen status."""

    __slots__ = ("_status",)

    def __init__(self, status: PolicyStatus):
        self._status = status
        super().__init__(status)

    @property
    def status(self) -> PolicyStatus:
        return self._status

    def __repr__(self) -> str:
        return f"RequestPolicyError(status={self._status!r})"


class _SystemClock:
    def monotonic(self) -> float:
        return asyncio.get_running_loop().time()

    def utcnow(self) -> datetime:
        return datetime.now(timezone.utc)

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


@dataclass
class _ProviderState:
    used: int = 0
    next_start: float = 0.0
    semaphore: asyncio.Semaphore | None = None
    rate_lock: asyncio.Lock | None = None


class RequestPolicyGate:
    """App-scope limiter and only allowed route to an open provider endpoint."""

    def __init__(
        self,
        policies: Mapping[str, ProviderPolicy],
        expected_policy_hashes: Mapping[str, str],
        *,
        live_enabled: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,
        resolver=None,
        clock=None,
        server_credentials: Mapping[str, SecretStr] | None = None,
    ):
        copied_policies = dict(policies)
        copied_hashes = dict(expected_policy_hashes)
        copied_credentials = dict(server_credentials or {})
        if set(copied_credentials) - {"ors"}:
            raise ValueError("unsupported provider credential name")
        if any(not isinstance(value, SecretStr) for value in copied_credentials.values()):
            raise TypeError("server credentials must be SecretStr values")
        self._policies = MappingProxyType(copied_policies)
        self._expected_hashes = MappingProxyType(copied_hashes)
        self._credentials = MappingProxyType(copied_credentials)
        self._live_enabled = bool(live_enabled)
        self._transport = transport
        self._injected_transport_invalid = (
            transport is not None and not isinstance(transport, httpx.MockTransport)
        )
        self._resolver = resolver or _resolve_addresses
        self._clock = clock or _SystemClock()
        self._states: dict[str, _ProviderState] = {}
        self._state_lock = asyncio.Lock()
        self._geocode_cache = OrderedDict()
        self._geocode_lock = asyncio.Lock()
        self._geocode_cache_hits = 0
        self._provider_failures: dict[str, dict[str, int]] = {}

    def __repr__(self) -> str:
        transport_name = "mock" if isinstance(self._transport, httpx.MockTransport) else "managed"
        return f"RequestPolicyGate(live_enabled={self._live_enabled}, transport={transport_name!r})"

    def claim(self, provider: str, capability: str, path: str) -> "_PermitContext":
        return _PermitContext(self, provider, capability, path)

    def assert_approved(self, provider: str, capability: str, path: str) -> ProviderPolicy:
        """Revalidate permission without DNS, budget claims or network traffic."""
        if not self._live_enabled:
            raise RequestPolicyError("NOT_CONFIGURED")
        if self._injected_transport_invalid:
            raise RequestPolicyError("CAPABILITY_UNVERIFIED")
        policy = self._policies.get(provider)
        expected_hash = self._expected_hashes.get(provider)
        if policy is None or expected_hash is None:
            raise RequestPolicyError("CAPABILITY_UNVERIFIED")
        if (policy.provider != provider or policy_digest(policy) != policy.policy_sha256 or
                policy.policy_sha256 != expected_hash):
            raise RequestPolicyError("CAPABILITY_UNVERIFIED")
        if self._clock.utcnow().astimezone(timezone.utc) >= policy.approved_until:
            raise RequestPolicyError("CAPABILITY_UNVERIFIED")
        if capability not in policy.allowed_capabilities or path not in policy.allowed_paths:
            raise RequestPolicyError("CAPABILITY_UNVERIFIED")
        if provider == "ors" and not self._secret("ors"):
            raise RequestPolicyError("NOT_CONFIGURED")
        return policy

    async def cached_geocode(self, key: str, fetch):
        """One app-scoped, bounded cache; concurrent identical misses coalesce."""
        policy = self.assert_approved("nominatim", "geocode", "/search")
        if policy.cache_policy != "MEMORY_24H":
            return await fetch()
        try:
            await asyncio.wait_for(self._geocode_lock.acquire(), timeout=10.0)
        except asyncio.TimeoutError:
            raise RequestPolicyError("RATE_LIMITED") from None
        try:
            self.assert_approved("nominatim", "geocode", "/search")
            now = self._clock.monotonic()
            for stale in [k for k, (expiry, _) in self._geocode_cache.items() if expiry <= now]:
                del self._geocode_cache[stale]
            if key in self._geocode_cache:
                self._geocode_cache_hits += 1
                self._geocode_cache.move_to_end(key)
                return self._geocode_cache[key][1].model_copy(deep=True)
            result = await fetch()
            self.assert_approved("nominatim", "geocode", "/search")
            if result.status in {"OK", "NO_MATCH", "AMBIGUOUS"}:
                self._geocode_cache[key] = (
                    self._clock.monotonic() + 86400, result.model_copy(deep=True),
                )
                self._geocode_cache.move_to_end(key)
                while len(self._geocode_cache) > 128:
                    self._geocode_cache.popitem(last=False)
            return result
        finally:
            self._geocode_lock.release()

    def observation_stats(self) -> dict:
        """Aggregate only: no credentials, queries, query hashes or positions."""
        return {
            "backend_attempts": {name: state.used for name, state in self._states.items()},
            "provider_failures": {
                name: counts.copy() for name, counts in self._provider_failures.items()
            },
            "cache_hits": self._geocode_cache_hits,
            "cache_entries": len(self._geocode_cache),
        }

    def record_provider_failure(self, provider: str, reason: str) -> None:
        if (not isinstance(provider, str) or provider != "osm_overpass"
                or not isinstance(reason, str) or reason not in _OVERPASS_FAILURE_CODES):
            raise ValueError("Invalid provider failure code")
        counts = self._provider_failures.setdefault(provider, {})
        counts[reason] = counts.get(reason, 0) + 1

    async def _claim(self, provider: str, capability: str, path: str) -> "RequestPermit":
        started = self._clock.monotonic()
        policy = self.assert_approved(provider, capability, path)

        deadline = started + policy.timeout_seconds
        host = urlsplit(policy.base_url).hostname
        if host is None:
            raise RequestPolicyError("CAPABILITY_UNVERIFIED")
        try:
            remaining = deadline - self._clock.monotonic()
            if remaining <= 0:
                raise RequestPolicyError("PROVIDER_ERROR")
            async with asyncio.timeout(remaining):
                addresses = await self._resolver(host)
        except RequestPolicyError:
            raise
        except (TimeoutError, asyncio.TimeoutError):
            raise RequestPolicyError("PROVIDER_ERROR") from None
        except Exception:
            raise RequestPolicyError("CAPABILITY_UNVERIFIED") from None
        if self._clock.monotonic() >= deadline:
            raise RequestPolicyError("PROVIDER_ERROR")
        public_address = _first_public_address(addresses)
        if public_address is None:
            raise RequestPolicyError("CAPABILITY_UNVERIFIED")
        if self._clock.utcnow().astimezone(timezone.utc) >= policy.approved_until:
            raise RequestPolicyError("CAPABILITY_UNVERIFIED")

        state = self._states.setdefault(
            provider,
            _ProviderState(semaphore=asyncio.Semaphore(1), rate_lock=asyncio.Lock()),
        )
        async with self._state_lock:
            if state.used >= policy.max_requests:
                raise RequestPolicyError("RATE_LIMITED")
            state.used += 1

        try:
            remaining = deadline - self._clock.monotonic()
            if remaining <= 0 or state.semaphore is None:
                raise RequestPolicyError("RATE_LIMITED")
            await asyncio.wait_for(state.semaphore.acquire(), timeout=remaining)
        except (TimeoutError, asyncio.TimeoutError):
            raise RequestPolicyError("RATE_LIMITED") from None
        if self._clock.monotonic() >= deadline:
            state.semaphore.release()
            raise RequestPolicyError("RATE_LIMITED")
        if self._clock.utcnow().astimezone(timezone.utc) >= policy.approved_until:
            state.semaphore.release()
            raise RequestPolicyError("CAPABILITY_UNVERIFIED")
        return RequestPermit(self, policy, path, host, public_address, state.semaphore, deadline)

    def _secret(self, provider: str) -> str:
        value = self._credentials.get(provider)
        return "" if value is None else value.get_secret_value()


class _PermitContext:
    def __init__(self, gate: RequestPolicyGate, provider: str, capability: str, path: str):
        self._gate = gate
        self._provider = provider
        self._capability = capability
        self._path = path
        self._permit: RequestPermit | None = None

    async def __aenter__(self) -> "RequestPermit":
        self._permit = await self._gate._claim(self._provider, self._capability, self._path)
        return self._permit

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        if self._permit is not None:
            self._permit._release()


class RequestPermit:
    def __init__(self, gate: RequestPolicyGate, policy: ProviderPolicy, path: str,
                 host: str, public_address: str, semaphore: asyncio.Semaphore, deadline: float):
        self._gate = gate
        self._policy = policy
        self._path = path
        self._host = host
        self._public_address = public_address
        self._semaphore = semaphore
        self._deadline = deadline
        self._sent = False
        self._released = False

    async def send(self, method: str, *, params=None, json_body=None, form=None) -> ProviderResponse:
        if self._released:
            raise RequestPolicyError("PROVIDER_ERROR")
        if self._sent:
            raise RequestPolicyError("PROVIDER_ERROR")
        self._sent = True
        method = method.upper()
        if method not in {"GET", "POST"}:
            raise RequestPolicyError("CAPABILITY_UNVERIFIED")
        secret = self._gate._secret(self._policy.provider)
        if secret and secret in repr((params, json_body, form)):
            raise RequestPolicyError("PROVIDER_ERROR")

        headers: dict[str, str] = {}
        if self._policy.user_agent:
            headers["User-Agent"] = self._policy.user_agent
        if self._policy.provider == "ors":
            if not secret:
                raise RequestPolicyError("NOT_CONFIGURED")
            headers["Authorization"] = secret

        try:
            base = httpx.URL(self._policy.base_url)
            url = base.copy_with(path=self._path)
            async with self._client() as client:
                request = client.build_request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    data=form,
                    headers=headers,
                )
                request.headers["Host"] = _host_header(self._host, base.port or 443)
                if not isinstance(self._gate._transport, httpx.MockTransport):
                    request.url = request.url.copy_with(host=self._public_address)
                    request.extensions["sni_hostname"] = self._host
                remaining = self._deadline - self._gate._clock.monotonic()
                if remaining <= 0:
                    raise RequestPolicyError("PROVIDER_ERROR")
                await self._wait_for_send_slot()
                remaining = self._deadline - self._gate._clock.monotonic()
                if remaining <= 0:
                    raise RequestPolicyError("PROVIDER_ERROR")
                async with asyncio.timeout(remaining):
                    response = await client.send(request, stream=True, follow_redirects=False)
                    try:
                        if 300 <= response.status_code < 400:
                            raise RequestPolicyError("PROVIDER_ERROR")
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > self._policy.max_response_bytes:
                                raise RequestPolicyError("PROVIDER_ERROR")
                            if self._gate._clock.monotonic() >= self._deadline:
                                raise RequestPolicyError("PROVIDER_ERROR")
                        if self._gate._clock.monotonic() >= self._deadline:
                            raise RequestPolicyError("PROVIDER_ERROR")
                        observed_at = self._gate._clock.utcnow().astimezone(timezone.utc)
                        evidence = (
                            "SYNTHETIC_FIXTURE"
                            if isinstance(self._gate._transport, httpx.MockTransport)
                            else "LIVE"
                        )
                        return ProviderResponse(
                            status_code=response.status_code,
                            body=bytes(body),
                            observed_at=observed_at,
                            evidence_kind=evidence,
                        )
                    finally:
                        await response.aclose()
        except RequestPolicyError:
            raise
        except (httpx.HTTPError, TimeoutError, asyncio.TimeoutError, ValueError, OSError):
            raise RequestPolicyError("PROVIDER_ERROR") from None

    def _client(self) -> httpx.AsyncClient:
        timeout = httpx.Timeout(
            self._policy.timeout_seconds,
            connect=self._policy.connect_timeout_seconds,
        )
        transport = self._gate._transport
        if transport is None:
            transport = httpx.AsyncHTTPTransport(retries=0, verify=True, trust_env=False)
        return httpx.AsyncClient(
            transport=transport,
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
        )

    async def _wait_for_send_slot(self) -> None:
        state = self._gate._states[self._policy.provider]
        if state.rate_lock is None:
            raise RequestPolicyError("PROVIDER_ERROR")
        async with state.rate_lock:
            now = self._gate._clock.monotonic()
            scheduled = max(now, state.next_start)
            delay = scheduled - now
            remaining = self._deadline - now
            if remaining <= 0 or scheduled >= self._deadline:
                raise RequestPolicyError("RATE_LIMITED")
            try:
                if delay > 0:
                    async with asyncio.timeout(remaining):
                        await self._gate._clock.sleep(delay)
            except (TimeoutError, asyncio.TimeoutError):
                raise RequestPolicyError("RATE_LIMITED") from None
            now = self._gate._clock.monotonic()
            if now >= self._deadline:
                raise RequestPolicyError("RATE_LIMITED")
            if self._gate._clock.utcnow().astimezone(timezone.utc) >= self._policy.approved_until:
                raise RequestPolicyError("CAPABILITY_UNVERIFIED")
            state.next_start = now + 1.0 / self._policy.max_rps

    def _release(self) -> None:
        if not self._released:
            self._released = True
            self._semaphore.release()


async def _resolve_addresses(host: str) -> tuple[str, ...]:
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        loop = asyncio.get_running_loop()
        infos = await loop.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return tuple(dict.fromkeys(item[4][0] for item in infos))
    return (str(literal),)


def _first_public_address(addresses) -> str | None:
    if isinstance(addresses, (str, bytes)):
        return None
    try:
        parsed = tuple(ipaddress.ip_address(str(address)) for address in addresses)
    except (TypeError, ValueError):
        return None
    if not parsed or any(not address.is_global for address in parsed):
        return None
    return str(parsed[0])


def _host_header(host: str, port: int) -> str:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        value = host
    else:
        value = f"[{address.compressed}]" if address.version == 6 else address.compressed
    return value if port == 443 else f"{value}:{port}"
