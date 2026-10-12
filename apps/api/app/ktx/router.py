import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from .catalog import KtxCatalog
from .repo import KtxRepository

router = APIRouter(prefix="/ktx", tags=["dormitories"])
log = logging.getLogger(__name__)
_engine = None


def init_ktx(engine):
    global _engine
    _engine = engine


def get_catalog():
    if _engine is None:
        raise HTTPException(503, "Danh mục KTX chưa sẵn sàng")
    try:
        catalog = KtxRepository(_engine).catalog()
    except SQLAlchemyError:
        log.warning("KTX catalogue has not been imported", exc_info=True)
        raise HTTPException(503, "Danh mục KTX đang được cập nhật")
    if catalog is None:
        raise HTTPException(503, "Danh mục KTX đang được cập nhật")
    return catalog


@router.get("", response_model=KtxCatalog)
def catalog():
    return get_catalog()


@router.get("/map")
def map_features():
    data = get_catalog()
    return {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "id": area.id,
             "geometry": {"type": "Point", "coordinates": [area.location.lng, area.location.lat]},
             "properties": {"name": area.name, "capacity": area.capacity, "url": "/ktx#khu-" + area.id.lower(),
                            "precision": area.location.precision, "location_label": area.location.label,
                            "source_url": area.location.source_url, "availability": "unknown"}}
            for area in data.dormitories
        ],
    }
