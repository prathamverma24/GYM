import pytest

from app.db import build_engine_options


def test_turso_engine_uses_libsql_dialect_and_auth_token():
    engine_url, connect_args = build_engine_options(
        "libsql://gym-example.turso.io",
        "secret-token",
    )

    assert engine_url == "sqlite+libsql://gym-example.turso.io?secure=true"
    assert connect_args == {"auth_token": "secret-token"}


def test_turso_engine_requires_an_auth_token():
    with pytest.raises(RuntimeError, match="TURSO_AUTH_TOKEN"):
        build_engine_options("libsql://gym-example.turso.io")


def test_local_sqlite_keeps_thread_compatibility_option():
    engine_url, connect_args = build_engine_options("sqlite:///./athleteos.db")

    assert engine_url == "sqlite:///./athleteos.db"
    assert connect_args == {"check_same_thread": False}
