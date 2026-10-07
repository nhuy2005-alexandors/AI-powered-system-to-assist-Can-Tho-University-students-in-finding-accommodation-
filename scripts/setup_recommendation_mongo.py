"""Create the recommendation collections and indexes in local MongoDB."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api"))
from app.room_service.recommendation.repo import ProfileRepository  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uri", default="mongodb://127.0.0.1:27018/")
    parser.add_argument("--database", default="nckh_recommendation_dev")
    args = parser.parse_args()
    repo = ProfileRepository(args.uri, args.database)
    try:
        db = repo.db()
        db.command("ping")
        print(f"MongoDB connected; database: {args.database}")
        for name in ("recommendation_profiles", "recommendation_interactions"):
            collection = db[name]
            print(
                f"{name}: documents={collection.count_documents({})}; "
                f"indexes={len(collection.index_information())}"
            )
        print("Collections ready. No user accounts or sample profiles were inserted.")
    except Exception as exc:
        # Keep URIs/credentials out of diagnostic output.
        detail = getattr(
            exc,
            "detail",
            "MongoDB unavailable; check Docker status and install requirements-recommendation.txt",
        )
        raise SystemExit(detail) from None
    finally:
        repo.close()


if __name__ == "__main__":
    main()
