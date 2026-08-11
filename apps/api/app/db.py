from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def build_engine_options(
    database_url: str,
    turso_auth_token: str | None = None,
) -> tuple[str, dict[str, object]]:
    if database_url.startswith("libsql://"):
        if not turso_auth_token:
            raise RuntimeError(
                "TURSO_AUTH_TOKEN must be set when TURSO_DATABASE_URL uses a remote Turso database."
            )
        separator = "&" if "?" in database_url else "?"
        return (
            f"sqlite+{database_url}{separator}secure=true",
            {"auth_token": turso_auth_token},
        )

    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return database_url, connect_args


configured_database_url = settings.turso_database_url or settings.database_url
engine_url, connect_args = build_engine_options(
    configured_database_url,
    settings.turso_auth_token,
)
engine = create_engine(engine_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
