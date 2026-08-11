"""Vercel Python entrypoint for the AthleteOS FastAPI application."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode


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


class RewrittenPathApp:
    """Restore the API path forwarded to Vercel's single Python function."""

    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            query = parse_qsl(scope.get("query_string", b"").decode(), keep_blank_values=True)
            forwarded_path = next(
                (value for key, value in query if key == "__athleteos_path"),
                None,
            )
            if forwarded_path and (
                forwarded_path == "/api/v1" or forwarded_path.startswith("/api/v1/")
            ):
                scope = dict(scope)
                scope["path"] = forwarded_path
                scope["raw_path"] = forwarded_path.encode()
                scope["query_string"] = urlencode(
                    [(key, value) for key, value in query if key != "__athleteos_path"],
                    doseq=True,
                ).encode()
        await self.application(scope, receive, send)


app = RewrittenPathApp(athleteos_app)
