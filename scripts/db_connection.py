"""Resolve a local PostgreSQL URL from docker-compose without assuming a host port."""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    env_path = ROOT / ".env"
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def local_database_url(override: str | None = None) -> str:
    if override:
        return override.replace("postgresql+psycopg://", "postgresql://", 1)
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    db_block = re.search(r"(?ms)^  db:\s*(.*?)(?=^  [a-zA-Z0-9_-]+:|^volumes:)", compose)
    if not db_block:
        raise RuntimeError("Không tìm thấy service db trong docker-compose.yml")
    port_match = re.search(r'["\']?(\d+)\s*:\s*5432["\']?', db_block.group(1))
    if not port_match:
        raise RuntimeError("Không tìm thấy host port PostgreSQL trong docker-compose.yml")
    values = _env_values()
    user = os.getenv("POSTGRES_USER", values.get("POSTGRES_USER", "nckh"))
    password = os.getenv("POSTGRES_PASSWORD", values.get("POSTGRES_PASSWORD", "nckh"))
    database = os.getenv("POSTGRES_DB", values.get("POSTGRES_DB", "nckh"))
    return f"postgresql://{user}:{password}@localhost:{port_match.group(1)}/{database}"
