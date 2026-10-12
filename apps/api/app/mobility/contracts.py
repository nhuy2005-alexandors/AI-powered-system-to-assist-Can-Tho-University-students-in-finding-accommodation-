"""Versioned mobility boundary: explicit units, provenance and unknown values."""
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    @field_validator("verified_at", "observed_at", "queried_at", check_fields=False)
    @classmethod
    def evidence_time(cls, value):
        if value is not None:
            if value.utcoffset() is None:
                raise ValueError("evidence timestamp must contain a UTC offset")
            return value.astimezone(timezone.utc)
        return value


class TravelMode(str, Enum):
    MOTORBIKE = "MOTORBIKE"
    WALK = "WALK"
    BICYCLE = "BICYCLE"
    BUS = "BUS"


CampusId = Literal["khu_i", "khu_ii", "khu_iii"]
PlaceCategory = Literal["grocery", "market", "pharmacy", "healthcare", "police", "bus_stop"]
EvidenceKind = Literal["NONE", "SYNTHETIC_FIXTURE", "LIVE"]
Precision = Literal["APPROXIMATE", "VERIFIED", "UNKNOWN"]
RouteStatus = Literal["NOT_CONFIGURED", "CAPABILITY_UNVERIFIED", "UNSUPPORTED_MODE",
                      "LOCATION_UNAVAILABLE", "NO_ROUTE", "RATE_LIMITED", "PROVIDER_ERROR", "OK"]
NearbyStatus = Literal["NOT_CONFIGURED", "CAPABILITY_UNVERIFIED", "UNSUPPORTED_CATEGORY",
                       "LOCATION_UNAVAILABLE", "EMPTY", "RATE_LIMITED", "PROVIDER_ERROR", "OK"]
GeocodeStatus = Literal["NOT_CONFIGURED", "CAPABILITY_UNVERIFIED", "UNSUPPORTED_REGION",
                        "NO_MATCH", "AMBIGUOUS", "RATE_LIMITED", "PROVIDER_ERROR", "OK"]


class Position(Contract):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    precision: Precision = "UNKNOWN"
    source: str | None = None
    verified_at: datetime | None = None

    @model_validator(mode="after")
    def verified_evidence(self):
        if self.precision == "VERIFIED" and (not self.source or self.verified_at is None):
            raise ValueError("verified position requires source and verification time")
        return self


class Campus(Contract):
    id: CampusId
    name: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    coordinate_version: str
    verification_status: Literal["PROVISIONAL", "VERIFIED"] = "PROVISIONAL"


class BoundingBox(Contract):
    south: float = Field(ge=-90, le=90)
    west: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)

    @model_validator(mode="after")
    def ordered(self):
        if self.south > self.north or self.west > self.east:
            raise ValueError("bbox extents must be ordered")
        return self


class CatalogListing(Contract):
    id: int = Field(gt=0)
    title: str
    source: str
    source_id: str
    source_url: str | None = None
    source_contact_url: str | None = None
    price: int | None = None
    area: float | None = None
    address: str | None = None
    district: str | None = None
    description: str | None = None
    images: list[str] = Field(default_factory=list)
    housing_type: str | None = None
    offer_kind: str | None = None
    description_state: str | None = None
    description_completeness: str | None = None
    description_is_partial: bool | None = None
    unit_type_uncertain: bool | None = None
    offer_context_uncertain: bool | None = None
    mixed_use_possible: bool | None = None
    lease_transfer_terms_verified: bool | None = None
    parsed_amenities: dict[str, bool | None] | None = None
    position: Position | None = None


class CatalogPage(Contract):
    items: list[CatalogListing]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=100)


class RouteRequest(Contract):
    listing_id: int = Field(gt=0)
    campus_id: CampusId
    requested_mode: TravelMode
    departure_time: datetime | None = None
    direction: Literal["LISTING_TO_CAMPUS"] = "LISTING_TO_CAMPUS"

    @field_validator("departure_time", mode="before")
    @classmethod
    def rfc3339_time(cls, value):
        if value is None or isinstance(value, datetime):
            return value
        if not isinstance(value, str) or not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value):
            raise ValueError("departure_time must be an RFC3339 string with offset")
        return value

    @field_validator("departure_time")
    @classmethod
    def aware_time(cls, value):
        if value is not None and value.utcoffset() is None:
            raise ValueError("departure_time must contain a UTC offset")
        return value

    @model_validator(mode="after")
    def bus_time(self):
        if self.requested_mode == TravelMode.BUS and self.departure_time is None:
            raise ValueError("BUS requires departure_time")
        return self


class LocationWarning(Contract):
    code: str
    severity: Literal["INFO", "CAUTION"]
    message: str
    evidence_source: str
    scope: str
    observed_at: datetime | None = None


class RouteResult(Contract):
    listing_id: int = Field(gt=0)
    campus_id: CampusId
    provider: str = "none"
    attribution: list[str] = Field(default_factory=list)
    provider_profile: str | None = None
    requested_mode: TravelMode
    effective_mode: TravelMode | None = None
    direction: Literal["LISTING_TO_CAMPUS"] = "LISTING_TO_CAMPUS"
    status: RouteStatus
    duration_seconds: float | None = Field(default=None, ge=0)
    distance_meters: float | None = Field(default=None, ge=0)
    polyline: list[Position] | None = None
    observed_at: datetime | None = None
    coordinate_version: str
    evidence_kind: EvidenceKind = "NONE"
    warnings: list[LocationWarning] = Field(default_factory=list)

    @model_validator(mode="after")
    def result_semantics(self):
        if self.status == "OK":
            if (self.duration_seconds is None or self.distance_meters is None or
                    self.effective_mode != self.requested_mode or self.evidence_kind == "NONE"):
                raise ValueError("OK requires measured units, matching mode and evidence")
        elif any(value is not None for value in (self.duration_seconds, self.distance_meters, self.polyline)):
            raise ValueError("failed route cannot contain measured units or geometry")
        return self


class NearbyRequest(Contract):
    listing_id: int = Field(gt=0)
    radius_m: Literal[500, 1000, 2000] = 1000
    categories: list[PlaceCategory] = Field(default_factory=lambda: [
        "grocery", "market", "pharmacy", "healthcare", "police", "bus_stop",
    ], min_length=1)

    @field_validator("categories")
    @classmethod
    def unique_categories(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("categories must be unique")
        return value


class Place(Contract):
    provider_place_id: str
    name: str
    category: PlaceCategory
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    straight_line_distance_m: float | None = Field(default=None, ge=0)
    attribution: list[str] = Field(default_factory=list)


class NearbyResult(Contract):
    listing_id: int = Field(gt=0)
    radius_m: Literal[500, 1000, 2000]
    categories: list[PlaceCategory]
    provider: str = "none"
    status: NearbyStatus
    evidence_kind: EvidenceKind = "NONE"
    items: list[Place] = Field(default_factory=list)
    queried_at: datetime | None = None
    center_precision: Precision = "UNKNOWN"
    coverage: Literal["UNKNOWN", "PARTIAL"] = "UNKNOWN"
    truncated: bool = False

    @model_validator(mode="after")
    def empty_semantics(self):
        if self.status in ("OK", "EMPTY"):
            if self.evidence_kind == "NONE" or self.coverage != "PARTIAL":
                raise ValueError("observed response requires evidence and bounded coverage")
            if (self.status == "EMPTY") != (len(self.items) == 0):
                raise ValueError("EMPTY and OK must match item count")
        else:
            if self.items or self.coverage != "UNKNOWN" or self.truncated:
                raise ValueError("failed nearby result must have unknown coverage and no places")
            if self.status in ("NOT_CONFIGURED", "CAPABILITY_UNVERIFIED", "UNSUPPORTED_CATEGORY", "LOCATION_UNAVAILABLE"):
                if self.evidence_kind != "NONE" or self.queried_at is not None:
                    raise ValueError("unobserved status cannot claim provider evidence")
        return self


class ResolvedRouteRequest(Contract):
    request: RouteRequest
    origin: Position
    destination: Campus


class ResolvedNearbyRequest(Contract):
    request: NearbyRequest
    center: Position


class GeocodeRequest(Contract):
    address: str = Field(min_length=1, max_length=512)
    bounds: BoundingBox

    @field_validator("address", mode="before")
    @classmethod
    def strip_address(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value


class GeocodeResult(Contract):
    provider: str
    status: GeocodeStatus
    position: Position | None = None
    candidate_count: int = Field(ge=0)
    queried_at: datetime | None = None
    evidence_kind: EvidenceKind = "NONE"
    attribution: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def geocode_semantics(self):
        unobserved_statuses = {
            "NOT_CONFIGURED", "CAPABILITY_UNVERIFIED", "UNSUPPORTED_REGION",
        }
        observed_statuses = {"OK", "NO_MATCH", "AMBIGUOUS"}
        error_statuses = {"RATE_LIMITED", "PROVIDER_ERROR"}

        if self.status in unobserved_statuses:
            if (self.position is not None or self.candidate_count != 0 or
                    self.queried_at is not None or self.evidence_kind != "NONE"):
                raise ValueError("preflight geocoding status must remain unobserved")
            return self

        if self.status in observed_statuses:
            if self.queried_at is None or self.evidence_kind == "NONE":
                raise ValueError("observed geocoding status requires timestamp and evidence")
            expected_count = {"OK": 1, "NO_MATCH": 0}.get(self.status)
            if expected_count is not None and self.candidate_count != expected_count:
                raise ValueError("geocoding status has inconsistent candidate count")
            if self.status == "AMBIGUOUS" and self.candidate_count < 2:
                raise ValueError("AMBIGUOUS requires at least two candidates")
            if self.status == "OK":
                if self.position is None or self.position.precision != "APPROXIMATE":
                    raise ValueError("OK geocoding requires one approximate position")
            elif self.position is not None:
                raise ValueError("only OK geocoding may contain a position")
            return self

        if self.status in error_statuses:
            if self.position is not None or self.candidate_count != 0:
                raise ValueError("geocoding errors cannot contain candidates or a position")
            if (self.evidence_kind == "NONE") != (self.queried_at is None):
                raise ValueError("error observation timestamp and evidence must be paired")
        return self
