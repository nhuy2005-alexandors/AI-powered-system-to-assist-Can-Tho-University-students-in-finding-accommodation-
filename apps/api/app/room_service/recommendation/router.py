"""Public read-only preview and authenticated profile/event routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import create_engine

from ...config import settings
from .repo import ListingRepository, ProfileRepository
from .schemas import (
    InteractionIn,
    InteractionOut,
    Preferences,
    PreviewRequest,
    ProfileOut,
    RecommendationsOut,
)
from .service import RecommendationService

router = APIRouter(prefix="/recommend", tags=["recommendation"])
_service = None
_engine = None
_owns_engine = False
_bearer = HTTPBearer(auto_error=False)


def init_recommendation(engine):
    global _service, _engine, _owns_engine
    _owns_engine = bool(settings.recommendation_database_url)
    _engine = (
        create_engine(settings.recommendation_database_url, pool_pre_ping=True)
        if _owns_engine
        else engine
    )
    _service = RecommendationService(
        ListingRepository(_engine),
        ProfileRepository(
            settings.recommendation_mongo_uri,
            settings.recommendation_mongo_database,
        ),
    )


def close_recommendation():
    if _service is not None:
        _service.profiles.close()
    if _owns_engine and _engine is not None:
        _engine.dispose()


def get_service():
    if _service is None:
        raise HTTPException(503, "Recommendation chưa khởi tạo")
    return _service


def get_recommendation_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
):
    """Replaced at app setup by the configured authentication dependency."""
    raise HTTPException(
        503,
        "Chưa bật xác thực cho gợi ý; dùng --with-auth ở bản local hoặc /recommend/preview",
    )


def bind_postgres_auth(app):
    """Use the shared PostgreSQL account and JWT validation."""
    from .auth import get_postgres_recommendation_user_id
    app.dependency_overrides[get_recommendation_user_id] = get_postgres_recommendation_user_id


@router.post("/preview", response_model=RecommendationsOut)
def preview(body: PreviewRequest, service=Depends(get_service)):
    preferences = Preferences(
        **body.model_dump(include={"needs", "max_price", "district"})
    )
    return service.recommend(preferences, body.top_k, body.rerank)


@router.put("/preferences", response_model=ProfileOut)
def save_preferences(
    body: Preferences,
    user_id=Depends(get_recommendation_user_id),
    service=Depends(get_service),
):
    return service.save_preferences(user_id, body)


@router.get("/preferences", response_model=ProfileOut)
def get_preferences(
    user_id=Depends(get_recommendation_user_id), service=Depends(get_service)
):
    return service.profile(user_id)


@router.get("/for-you", response_model=RecommendationsOut)
def for_you(
    top_k: int = Query(default=10, ge=1, le=20),
    rerank: bool = False,
    user_id=Depends(get_recommendation_user_id),
    service=Depends(get_service),
):
    return service.for_you(user_id, top_k, rerank)


@router.post("/interactions", response_model=InteractionOut, status_code=201)
def record_interaction(
    body: InteractionIn,
    user_id=Depends(get_recommendation_user_id),
    service=Depends(get_service),
):
    return service.record(user_id, body)
