"""Build user-facing cautions only from explicit catalog and route evidence."""
from .campuses import get_campus
from .contracts import CatalogListing, LocationWarning, RouteResult


def build_warnings(listing: CatalogListing, route: RouteResult | None) -> list[LocationWarning]:
    warnings: list[LocationWarning] = []

    def add(code: str, message: str, evidence_source: str, scope: str) -> None:
        warnings.append(LocationWarning(
            code=code,
            severity="CAUTION",
            message=message,
            evidence_source=evidence_source,
            scope=scope,
        ))

    position = listing.position
    if position is None or position.precision == "UNKNOWN":
        add("LOCATION_UNKNOWN", "Vị trí tin đăng chưa được xác minh.", "catalog_position", "listing")
    elif position.precision == "APPROXIMATE":
        add("APPROXIMATE_LOCATION", "Vị trí trên bản đồ chỉ gần đúng; hãy xác nhận địa điểm cụ thể.",
            "catalog_position_precision", "listing")

    if route is not None:
        campus = get_campus(route.campus_id)
        if campus.verification_status != "VERIFIED":
            add("ENTRANCE_UNVERIFIED", "Tọa độ cổng trường chỉ là tạm thời, chưa được xác minh.",
                "campus_registry", "campus")

    route_observed = (route is not None and route.status == "OK" and
                      route.evidence_kind == "LIVE")
    if not route_observed:
        add("ROUTE_NOT_VERIFIED", "Chưa xác minh tuyến này bằng dữ liệu chỉ đường thực tế.",
            "route_status_and_provenance", "route")

    if listing.description_is_partial is True or listing.description_state == "PARTIAL":
        add("PARTIAL_DESCRIPTION", "Mô tả tin đăng chưa đầy đủ.",
            "catalog_description_flags", "listing")

    offer_kind = (listing.offer_kind or "").strip().casefold()
    transfer_context_needs_warning = (
        offer_kind in {"", "unknown", "lease_transfer"} or
        listing.offer_context_uncertain is True
    )
    if transfer_context_needs_warning and listing.lease_transfer_terms_verified is not True:
        add("TRANSFER_TERMS_UNVERIFIED", "Chưa xác minh điều kiện thuê hoặc sang nhượng.",
            "catalog_transfer_terms_flag", "listing")

    if listing.unit_type_uncertain is not False:
        add("UNIT_TYPE_UNKNOWN", "Chưa xác định rõ loại hình chỗ ở được cho thuê.",
            "catalog_unit_type_flag", "listing")

    if (route is not None and route.status == "OK" and route.provider.lower() == "google" and
            route.requested_mode.value in {"WALK", "BICYCLE", "MOTORBIKE"}):
        add("GOOGLE_ROUTE_BETA",
            "Các tuyến đi bộ, xe đạp và xe máy của Google đang ở giai đoạn beta; dữ liệu có thể chưa thể hiện đầy đủ vỉa hè, lối đi bộ hoặc đường dành cho xe đạp.",
            "Google Routes API RouteTravelMode documentation", "route")

    return warnings
