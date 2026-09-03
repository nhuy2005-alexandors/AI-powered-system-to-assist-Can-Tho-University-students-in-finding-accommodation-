from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
import httpx
import redis

from .config import settings
from .crawler import ListingRepo, build_scheduler, run_source
from .listings import init_listings, listings_router
from .auth import AuthRepo, auth_router, init_auth, init_auth_deps
from .room_service import chatbot_router, init_chatbot, init_risk, risk_router
from .room_service.risk.repo import RiskRepository
from .room_service.risk.service import RiskService
from .reports import init_reports, reports_router

log = logging.getLogger("app.main")

# psycopg3 sync engine; pre_ping avoids stale conns after db restart
engine = create_engine(settings.database_url, pool_pre_ping=True)
redis_client = redis.from_url(settings.redis_url, decode_responses=True)
init_listings(engine)
init_auth(engine)
init_auth_deps(AuthRepo(engine))
init_chatbot(engine)
init_risk(engine)
init_reports(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = None
    if settings.crawler_enabled:
        scheduler = build_scheduler(engine)
        scheduler.start()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)
    engine.dispose()
    redis_client.close()


app = FastAPI(title="NCKH API", version="0.1.0", lifespan=lifespan)
app.include_router(listings_router)
app.include_router(auth_router)
app.include_router(chatbot_router)
app.include_router(risk_router)
app.include_router(reports_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/deps")
def health_deps():
    checks: dict[str, str] = {}

    try:
        with engine.connect() as conn:
            postgis = conn.execute(text("SELECT PostGIS_Version()")).scalar()
            has_vector = conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
        checks["postgres"] = "ok"
        checks["postgis"] = postgis or "missing"
        checks["pgvector"] = "ok" if has_vector else "missing"
    except Exception as exc:  # surface the failing dep instead of 500
        checks["postgres"] = f"error: {exc}"

    try:
        checks["redis"] = "ok" if redis_client.ping() else "down"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    return checks


@app.get("/health/ai")
def health_ai():
    """Không lộ secret: chỉ báo provider/model và khả năng nhìn thấy Ollama."""
    qwen_status = "not-selected"
    if settings.chatbot_llm_provider in ("auto", "qwen"):
        try:
            response = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=3)
            response.raise_for_status()
            models = {item.get("name") for item in response.json().get("models", [])}
            qwen_status = "ok" if settings.ollama_model in models else "model-missing"
        except Exception:
            qwen_status = "unreachable"
    return {
        "provider_mode": settings.chatbot_llm_provider,
        "qwen": {"status": qwen_status, "model": settings.ollama_model},
        "gemini": {"configured": bool(settings.gemini_api_key), "model": settings.gemini_model},
        "embedding_model": settings.chatbot_embedding_model,
        "risk_auto_assess": settings.risk_auto_assess,
    }


@app.get("/crawler/status")
def crawler_status(limit: int = 10):
    """Lần crawl gần nhất mỗi nguồn — health check cho Admin Dashboard (C2.1/C2.3)."""
    return {"enabled": settings.crawler_enabled, "runs": ListingRepo(engine).latest_runs(limit)}


@app.post("/crawler/run")
async def crawler_run(source: str = "phongtro123", mode: str = "incremental"):
    """Trigger thủ công 1 nguồn (Admin/test). mode: 'incremental' | 'full'."""
    if mode not in ("incremental", "full"):
        raise HTTPException(400, "mode phải là 'incremental' hoặc 'full'")
    counts = await run_source(source, mode, ListingRepo(engine))
    # làm sạch ngay để manual run cũng cho ra data 'cleaned' (không kẹt ở 'raw')
    from .cleaner.pipeline import run_cleaner
    run_cleaner(engine)
    risk_processed = 0
    if settings.risk_auto_assess:
        try:
            risk_processed = RiskService(RiskRepository(engine)).assess_pending(
                settings.risk_auto_assess_limit
            ).processed
        except Exception:  # enrichment lỗi không làm mất kết quả crawl
            log.exception("risk auto-assess failed after manual crawler run")
    return {"source": source, "mode": mode, "risk_processed": risk_processed, **counts}
