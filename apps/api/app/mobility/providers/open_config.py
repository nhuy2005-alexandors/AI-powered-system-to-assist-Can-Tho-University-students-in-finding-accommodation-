"""Separate fail-closed settings for the open mobility provider lane."""
from typing import Literal
from urllib.parse import urlsplit

import ipaddress
from pydantic import Field, PrivateAttr, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ProviderChoice = Literal["disabled", "ors", "osm_overpass", "nominatim"]


class OpenMobilitySettings(BaseSettings):
    """Open mobility configuration; legacy Google fields are intentionally absent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MOBILITY_",
        extra="ignore",
        frozen=True,
        allow_inf_nan=False,
        populate_by_name=True,
    )

    enabled: bool = False
    live_enabled: bool = False
    google_maps_enabled: bool = Field(default=False, validation_alias="GOOGLE_MAPS_ENABLED")
    routing_provider: Literal["disabled", "ors"] = "disabled"
    places_provider: Literal["disabled", "osm_overpass"] = "disabled"
    geocoder_provider: Literal["disabled", "nominatim"] = "disabled"
    ors_api_key: SecretStr = SecretStr("")
    ors_base_url: str = ""
    overpass_url: str = ""
    nominatim_url: str = ""
    tiles_enabled: bool = False
    tile_url: str = ""
    tile_attribution: str = ""
    allowed_tile_origin: str = ""
    provider_policies: dict[str, "ProviderPolicy"] = Field(default_factory=dict, repr=False)
    expected_policy_hashes: dict[str, str] = Field(default_factory=dict, repr=False)

    _request_policy_gate = PrivateAttr(default=None)
    _request_policy_transport = PrivateAttr(default=None)
    _request_policy_resolver = PrivateAttr(default=None)
    _request_policy_clock = PrivateAttr(default=None)

    @field_validator("google_maps_enabled")
    @classmethod
    def reject_google_runtime(cls, value: bool) -> bool:
        if value:
            raise ValueError("Google Maps runtime is not supported by open mobility")
        return value

    @field_validator("ors_base_url", "overpass_url", "nominatim_url", "tile_url", "allowed_tile_origin")
    @classmethod
    def safe_https_endpoint(cls, value: str) -> str:
        value = value.strip()
        if not value:
            return value
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("mobility endpoints must be HTTPS without credentials, query, or fragment")
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            host = parsed.hostname.lower().rstrip(".")
            if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
                raise ValueError("mobility endpoint host is not public")
        else:
            if not address.is_global:
                raise ValueError("mobility endpoint host is not public")
        if any(part in {".", ".."} for part in parsed.path.split("/")) or "\\" in parsed.path:
            raise ValueError("mobility endpoint path is invalid")
        return value

    @model_validator(mode="after")
    def tile_configuration_is_complete(self):
        if self.tiles_enabled:
            if not self.tile_url or not self.tile_attribution.strip() or not self.allowed_tile_origin:
                raise ValueError("enabled tiles require URL, attribution, and allowed origin")
            if _origin(self.tile_url) != _origin(self.allowed_tile_origin):
                raise ValueError("tile URL must match the separately allowlisted origin")
        return self

    @property
    def request_policy_gate(self):
        """Return one immutable, app-scope gate shared by all provider factories."""
        return self.get_request_policy_gate()

    def get_request_policy_gate(self, *, transport=None, resolver=None, clock=None):
        """Get the app gate, binding constructor-only test seams at most once."""
        if self._request_policy_gate is None:
            from .network_policy import RequestPolicyGate

            policies = {
                name: policy
                for name, policy in self.provider_policies.items()
                if _configured_endpoint_matches(self, name, policy)
            }
            credentials = (
                {"ors": self.ors_api_key}
                if self.ors_api_key.get_secret_value()
                else {}
            )
            gate = RequestPolicyGate(
                policies=policies,
                expected_policy_hashes=self.expected_policy_hashes,
                live_enabled=self.live_enabled,
                transport=transport,
                resolver=resolver,
                clock=clock,
                server_credentials=credentials,
            )
            object.__setattr__(self, "_request_policy_gate", gate)
            object.__setattr__(self, "_request_policy_transport", transport)
            object.__setattr__(self, "_request_policy_resolver", resolver)
            object.__setattr__(self, "_request_policy_clock", clock)
        elif ((transport is not None and transport is not self._request_policy_transport) or
              (resolver is not None and resolver is not self._request_policy_resolver) or
              (clock is not None and clock is not self._request_policy_clock)):
            raise ValueError("policy gate test seams are already bound")
        return self._request_policy_gate

    def map_config(self) -> dict[str, object]:
        enabled = self.enabled and self.tiles_enabled
        return {
            "enabled": enabled,
            "tileUrl": self.tile_url if enabled else None,
            "attribution": self.tile_attribution if enabled else "",
            "allowedTileOrigin": self.allowed_tile_origin if enabled else None,
        }


def _origin(value: str) -> tuple[str, str, int]:
    parsed = urlsplit(value)
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.port or 443


def _configured_endpoint_matches(settings: OpenMobilitySettings, provider: str, policy) -> bool:
    setting_name = {
        "ors": "ors_base_url",
        "osm_overpass": "overpass_url",
        "nominatim": "nominatim_url",
    }.get(provider)
    configured = "" if setting_name is None else getattr(settings, setting_name)
    if not configured:
        return False
    configured_parts = urlsplit(configured)
    policy_parts = urlsplit(policy.base_url)
    if _origin(configured) != _origin(policy.base_url):
        return False
    return configured_parts.path in ("", "/") or configured_parts.path in policy.allowed_paths


# Resolve the forward annotation only after the policy module has been imported.
from .network_policy import ProviderPolicy  # noqa: E402

OpenMobilitySettings.model_rebuild()
