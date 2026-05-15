import asyncio
import enum as pyenum
import json
import os
import uuid
from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Column
from sqlalchemy import MetaData
from sqlalchemy import bindparam
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.types import TypeDecorator
from sqlalchemy.ext.asyncio import create_async_engine

from clickhouse_sqlalchemy import engines
from clickhouse_sqlalchemy import Table
from clickhouse_sqlalchemy import types as ch_types


class _ProcessingState(pyenum.IntEnum):
    created = 1
    running = 2
    failed = 3


class _RedactedPayload(TypeDecorator):
    impl = ch_types.String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps({"wrapped": value}, sort_keys=True)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)["wrapped"]


def _load_dotenv_test():
    candidates = []
    explicit = os.environ.get("TEST_ENV_FILE")
    if explicit:
        candidates.append(Path(explicit))

    candidates.extend(parent / ".env.test" for parent in (Path.cwd(), *Path.cwd().parents))

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


def _table_name(prefix):
    return f"test_ch_compat_{prefix}_{uuid.uuid4().hex[:8]}"


def _fixed_hex(length):
    return "a" * length


def _uuid(index=1):
    return f"00000000-0000-4000-8000-{index:012d}"


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


async def _drop(engine, table):
    async with engine.begin() as conn:
        await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))


async def _execute_each(conn, statement, rows):
    if isinstance(rows, dict):
        await conn.execute(statement, rows)
        return

    for row in rows:
        await conn.execute(statement, row)


def _assert_ms(value, expected_microsecond):
    assert value.microsecond == expected_microsecond


__all__ = [
    "asyncio",
    "bindparam",
    "ch_types",
    "Column",
    "date",
    "datetime",
    "Decimal",
    "engines",
    "json",
    "MetaData",
    "pytest",
    "select",
    "Table",
    "text",
    "timedelta",
    "uuid",
    "_ProcessingState",
    "_RedactedPayload",
    "_assert_ms",
    "_drop",
    "_engine",
    "_execute_each",
    "_fixed_hex",
    "_table_name",
    "_uuid",
]
