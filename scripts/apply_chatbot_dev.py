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

    migration = (ROOT / "infra/db/migrations/90_chatbot.sql").read_text(encoding="utf-8")
    seed_path = ROOT / "infra/db/seeds/dev_chatbot.sql"
    if not args.skip_seed and not seed_path.exists():
        raise SystemExit("Chưa có dev seed; chạy scripts/generate_fake_listings.py trước")
    with psycopg.connect(local_database_url(args.database_url), autocommit=True) as conn:
        conn.execute(migration)
        if not args.skip_seed:
            conn.execute(seed_path.read_text(encoding="utf-8"))
    print("Applied 90_chatbot.sql" + (" and dev_chatbot.sql" if not args.skip_seed else ""))


if __name__ == "__main__":
    main()
