"""Vercel Python entrypoint for the AthleteOS FastAPI application."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _database_url() -> str:
    value = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not value:
        # This keeps an unconfigured preview usable for smoke testing. Vercel's
        # /tmp filesystem is ephemeral, so production must configure Postgres.
        return "sqlite:////tmp/athleteos.db"
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


os.environ.setdefault("APP_ENV", "production")
os.environ.setdefault("SESSION_COOKIE_SECURE", "true")
os.environ.setdefault("AUTO_CREATE_DB", "true")
os.environ["DATABASE_URL"] = _database_url()

# This makes the entrypoint directly importable during local tests. On Vercel,
# the same package is installed from ../api by requirements.txt.
backend_root = Path(__file__).resolve().parents[2] / "api"
if backend_root.exists():
    sys.path.insert(0, str(backend_root))

from app.main import app as athleteos_app

app = athleteos_app
