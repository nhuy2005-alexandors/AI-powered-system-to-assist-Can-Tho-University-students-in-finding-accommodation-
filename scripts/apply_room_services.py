"""Apply additive chatbot and risk migrations to an existing database volume."""
from __future__ import annotations

import argparse

from db_connection import ROOT, local_database_url


MIGRATIONS = (
    ROOT / "infra/db/migrations/90_chatbot.sql",
    ROOT / "infra/db/migrations/91_room_service_risk.sql",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", help="Override URL; otherwise read Compose host port")
    args = parser.parse_args()
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit("Cần cài psycopg; hãy dùng Python của apps/api hoặc container API") from exc

    with psycopg.connect(local_database_url(args.database_url), autocommit=True) as conn:
        for migration in MIGRATIONS:
            conn.execute(migration.read_text(encoding="utf-8"))
            print(f"Applied {migration.name}")


if __name__ == "__main__":
    main()
