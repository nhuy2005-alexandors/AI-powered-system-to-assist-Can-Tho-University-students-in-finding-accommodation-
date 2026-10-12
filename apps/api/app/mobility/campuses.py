"""One registry for the new lane. Legacy coordinates are provisional entrances."""
from .contracts import Campus, CampusId

COORDINATE_VERSION = "legacy-2026-07-06-provisional"
CAMPUSES = tuple(Campus(id=id_, name=name, lat=lat, lng=lng,
                       coordinate_version=COORDINATE_VERSION) for id_, name, lat, lng in (
    ("khu_i", "Khu I", 10.0159, 105.7656),
    ("khu_ii", "Khu II", 10.0322, 105.7683),
    ("khu_iii", "Khu III", 10.0340, 105.7798),
))


def get_campus(campus_id: CampusId) -> Campus:
    for campus in CAMPUSES:
        if campus.id == campus_id:
            return campus.model_copy(deep=True)
    raise ValueError("unknown campus")
