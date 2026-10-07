"""Run the preview (8001) or full API (8000) against the local handoff database."""
from __future__ import annotations

import argparse
import getpass
import secrets
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import URL, create_engine
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api"))
from app.room_service.recommendation.router import (  # noqa: E402
    bind_postgres_auth,
    close_recommendation,
    init_recommendation,
    router,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-auth",
        action="store_true",
        help="Enable PostgreSQL/JWT login and saved recommendation profiles",
    )
    parser.add_argument(
        "--full-api",
        action="store_true",
        help="Run app.main with shared handoff accounts/catalog (default port 8000)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Override the local port (preview: 8001, full API: 8000)",
    )
    args = parser.parse_args()
    port = args.port if args.port is not None else (8000 if args.full_api else 8001)
    if not 1 <= port <= 65535:
        parser.error("port must be between 1 and 65535")
    from app.config import settings

    if args.with_auth or args.full_api:
        if not settings.recommendation_mongo_uri:
            settings.recommendation_mongo_uri = "mongodb://127.0.0.1:27018/"
            settings.recommendation_mongo_database = "nckh_recommendation_dev"
        if settings.jwt_secret == "dev-insecure-change-me":
            settings.jwt_secret = secrets.token_urlsafe(48)
            print(
                "Local JWT secret generated for this run; log in again after restarting the API."
            )
    password = getpass.getpass("Mat khau PostgreSQL handoff: ")
    database_url = URL.create(
        "postgresql+psycopg",
        username="nckh_handoff",
        password=password,
        host="localhost",
        port=5454,
        database="nckh_handoff",
    )
    if args.full_api:
        # Set the database before importing app.main, which creates its engines.
        settings.database_url = database_url.render_as_string(hide_password=False)
        settings.recommendation_database_url = ""
        settings.recommendation_auth_source = "postgres"
        settings.crawler_enabled = False
        if settings.redis_url == "redis://redis:6379/0":
            settings.redis_url = "redis://127.0.0.1:6379/0"
        from app.main import app

        print(
            "Full API: shared PostgreSQL handoff accounts/catalog; recommendation auth enabled."
        )
        print("Automatic crawling is disabled for this local integration run.")
        print(f"Open http://127.0.0.1:{port}/docs")
        uvicorn.run(app, host="127.0.0.1", port=port)
        return

    engine = create_engine(database_url, pool_pre_ping=True)
    init_recommendation(engine)

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            close_recommendation()
            engine.dispose()

    app = FastAPI(title="Recommendation local preview", lifespan=lifespan)
    app.include_router(router)
    if args.with_auth:
        from app.auth import AuthRepo, auth_router, init_auth, init_auth_deps

        init_auth(engine)
        init_auth_deps(AuthRepo(engine))
        app.include_router(auth_router)
        bind_postgres_auth(app)
        print("Local auth enabled: PostgreSQL accounts; MongoDB recommendation profiles/events.")
    print(f"Open http://127.0.0.1:{port}/docs")
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
