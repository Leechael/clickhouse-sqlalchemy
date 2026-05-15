import os
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def _load_dotenv_test():
    candidates = []
    explicit = os.environ.get("TEST_ENV_FILE")
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend(
        parent / ".env.test" for parent in (Path.cwd(), *Path.cwd().parents)
    )
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _clickhouse_url():
    _load_dotenv_test()
    return os.environ.get(
        "TEST_CLICKHOUSE_URL",
        "clickhouse+asynch://default:@127.0.0.1:9000/default",
    )


def _engine():
    return create_async_engine(
        _clickhouse_url(),
        connect_args={
            "settings": {
                "async_insert": 1,
                "wait_for_async_insert": 1,
            },
        },
    )


def _table_name(prefix):
    return f"test_ch_compat_{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_datetime64_textual_insert_preserves_millisecond_precision():
    """DateTime64(3) values bound via text() keep sub-second precision."""
    table = _table_name("dt64_precision")
    engine = _engine()
    value = datetime(2026, 1, 1, 0, 0, 0, 123000)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        id UInt64,
                        ts DateTime64(3)
                    )
                    ENGINE = MergeTree
                    ORDER BY id
                    """
                )
            )
            await conn.execute(
                text(f"INSERT INTO {table} (id, ts) VALUES (:id, :ts)"),
                {"id": 1, "ts": value},
            )

            result = await conn.execute(
                text(f"SELECT ts FROM {table} WHERE id = :id"),
                {"id": 1},
            )
            row = result.one()
            assert row.ts.microsecond == 123000
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        await engine.dispose()


@pytest.mark.asyncio
async def test_datetime_textual_insert_does_not_append_zero_fraction():
    """Plain DateTime bound via text() stays at second precision."""
    table = _table_name("dt_precision")
    engine = _engine()
    value = datetime(2026, 1, 1, 0, 0, 0)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        id UInt64,
                        ts DateTime
                    )
                    ENGINE = MergeTree
                    ORDER BY id
                    """
                )
            )
            await conn.execute(
                text(f"INSERT INTO {table} (id, ts) VALUES (:id, :ts)"),
                {"id": 1, "ts": value},
            )

            result = await conn.execute(
                text(f"SELECT ts FROM {table} WHERE id = :id"),
                {"id": 1},
            )
            row = result.one()
            assert row.ts.microsecond == 0
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        await engine.dispose()
