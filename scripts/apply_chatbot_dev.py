"""Apply only the additive chatbot migration and controlled development seed."""
from __future__ import annotations

import argparse
from pathlib import Path

from db_connection import ROOT, local_database_url


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", help="Override URL; otherwise read Compose host port")
    parser.add_argument("--skip-seed", action="store_true")
    args = parser.parse_args()
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit("Cần cài psycopg; hãy chạy script trong container API hoặc Python 3.12") from exc

    migrations = [
        ROOT / "infra/db/migrations/90_chatbot.sql",
        ROOT / "infra/db/migrations/91_room_service_risk.sql",
        ROOT / "infra/db/migrations/92_reports_moderation.sql",
        ROOT / "infra/db/migrations/93_ai_product_features.sql",
        ROOT / "infra/db/migrations/94_legal_knowledge.sql",
        ROOT / "infra/db/migrations/95_fr_delivery.sql",
        ROOT / "infra/db/migrations/96_reviews_sentiment.sql",
        ROOT / "infra/db/migrations/97_response_performance.sql",
        ROOT / "infra/db/migrations/98_legal_quality.sql",
        ROOT / "infra/db/migrations/99_chat_history.sql",
        ROOT / "infra/db/migrations/100_shared_answers_document_control.sql",
    ]
    seed_path = ROOT / "infra/db/seeds/dev_chatbot.sql"
    if not args.skip_seed and not seed_path.exists():
        raise SystemExit("Chưa có dev seed; chạy scripts/generate_fake_listings.py trước")
    with psycopg.connect(local_database_url(args.database_url), autocommit=True) as conn:
        for migration in migrations:
            conn.execute(migration.read_text(encoding="utf-8"))
        if not args.skip_seed:
            conn.execute(seed_path.read_text(encoding="utf-8"))
    print("Applied room-service migrations" + (" and dev_chatbot.sql" if not args.skip_seed else ""))


if __name__ == "__main__":
    main()
