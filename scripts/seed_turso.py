"""Seed AthleteOS reference catalogues into an empty Turso database over HTTP."""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "apps" / "api"))
TURSO_DATABASE_URL = os.environ.pop("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.environ.pop("TURSO_AUTH_TOKEN", "")
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("APP_ENV", "catalogue-seed")

from app import models  # noqa: F401
from app.db import Base
from app.domains.catalog import seed_catalogues

TABLES = (
    "exercises",
    "progression_rule_definitions",
    "exercise_substitution_groups",
    "workout_split_templates",
    "workout_day_templates",
    "workout_prescription_templates",
    "program_selection_rules",
    "research_sources",
    "foods",
    "food_aliases",
    "serving_options",
)
BATCH_SIZE = 75


def turso_value(value: object) -> dict[str, object]:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bytes):
        return {"type": "blob", "base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    return {"type": "text", "value": str(value)}


def pipeline(endpoint: str, token: str, statements: list[dict]) -> list[dict]:
    payload = json.dumps(
        {"requests": [{"type": "execute", "stmt": statement} for statement in statements] + [{"type": "close"}]}
    ).encode()
    request = Request(
        f"{endpoint}/v2/pipeline",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(
            f"Turso returned HTTP {error.code} while seeding catalogues: {detail}"
        ) from error

    errors = [item for item in result["results"][:-1] if item["type"] != "ok"]
    if errors:
        raise RuntimeError(f"Turso rejected a catalogue batch: {errors[0]}")
    return result["results"][:-1]


def remote_counts(endpoint: str, token: str) -> dict[str, int]:
    statements = [{"sql": f'SELECT COUNT(*) FROM "{table}"', "args": []} for table in TABLES]
    results = pipeline(endpoint, token, statements)
    return {
        table: int(result["response"]["result"]["rows"][0][0]["value"])
        for table, result in zip(TABLES, results, strict=True)
    }


def local_catalogue() -> tuple[dict[str, tuple[list[str], list[tuple]]], dict[str, int]]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        seed_catalogues(session)

    catalogue: dict[str, tuple[list[str], list[tuple]]] = {}
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for table in TABLES:
            result = connection.exec_driver_sql(f'SELECT * FROM "{table}"')
            rows = [tuple(row) for row in result]
            catalogue[table] = (list(result.keys()), rows)
            counts[table] = len(rows)
    engine.dispose()
    return catalogue, counts


def main() -> None:
    database_url = TURSO_DATABASE_URL
    token = TURSO_AUTH_TOKEN
    if not database_url.startswith("libsql://") or not token:
        raise SystemExit("Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN before running this script.")
    endpoint = database_url.replace("libsql://", "https://", 1).rstrip("/")

    catalogue, expected_counts = local_catalogue()
    existing_counts = remote_counts(endpoint, token)
    if existing_counts == expected_counts:
        print("Turso reference catalogues are already current.")
        return
    invalid_counts = {
        table: count
        for table, count in existing_counts.items()
        if count not in {0, expected_counts[table]}
    }
    if invalid_counts:
        raise SystemExit(
            "Refusing to seed partially populated Turso tables. Back them up and clear only the "
            f"incomplete reference tables before retrying: {invalid_counts}"
        )

    for table in TABLES:
        columns, rows = catalogue[table]
        if existing_counts[table] == expected_counts[table]:
            print(f"Verified {len(rows)} existing rows in {table}.")
            continue
        quoted_columns = ", ".join(f'"{column}"' for column in columns)
        row_placeholders = f"({', '.join('?' for _ in columns)})"
        for offset in range(0, len(rows), BATCH_SIZE):
            batch = rows[offset : offset + BATCH_SIZE]
            placeholders = ", ".join(row_placeholders for _ in batch)
            sql = f'INSERT INTO "{table}" ({quoted_columns}) VALUES {placeholders}'
            statements = [
                {"sql": "BEGIN", "args": []},
                {
                    "sql": sql,
                    "args": [turso_value(value) for row in batch for value in row],
                },
                {"sql": "COMMIT", "args": []},
            ]
            pipeline(endpoint, token, statements)
        print(f"Seeded {len(rows)} rows into {table}.")

    final_counts = remote_counts(endpoint, token)
    if final_counts != expected_counts:
        raise RuntimeError(f"Turso catalogue verification failed: {final_counts}")
    print("Turso reference catalogue seed completed successfully.")


if __name__ == "__main__":
    main()
