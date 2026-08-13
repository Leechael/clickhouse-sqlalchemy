from datetime import datetime

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import text

from clickhouse_sqlalchemy.drivers.asynch.connector import AsyncAdapt_asynch_dbapi
from tests.drivers.asynch._core_query_helpers import (
    _drop,
    _engine,
    _execute_each,
    _table_name,
)


class FakeAsynch:
    class errors:
        class Error(Exception):
            pass
        class ServerException(Exception):
            pass
        class UnexpectedPacketFromServerError(Exception):
            pass
        class LogicalError(Exception):
            pass
        class UnknownTypeError(Exception):
            pass
        class ChecksumDoesntMatchError(Exception):
            pass
        class TypeMismatchError(Exception):
            pass
        class UnknownCompressionMethod(Exception):
            pass
        class TooLargeStringSize(Exception):
            pass
        class NetworkError(Exception):
            pass
        class SocketTimeoutError(Exception):
            pass
        class UnknownPacketFromServerError(Exception):
            pass
        class CannotParseUuidError(Exception):
            pass
        class CannotParseDomainError(Exception):
            pass
        class PartiallyConsumedQueryError(Exception):
            pass
        class ColumnException(Exception):
            pass
        class ColumnTypeMismatchException(Exception):
            pass
        class StructPackException(Exception):
            pass
        class InterfaceError(Exception):
            pass
        class DatabaseError(Exception):
            pass
        class DataError(Exception):
            pass
        class OperationalError(Exception):
            pass
        class IntegrityError(Exception):
            pass
        class InternalError(Exception):
            pass
        class ProgrammingError(Exception):
            pass
        class NotSupportedError(Exception):
            pass

    class connection:
        class Connection:
            def __init__(self, *args, **kwargs):
                self._args = args
                self._kwargs = kwargs


def test_connect_injects_join_use_nulls_by_default():
    dbapi = AsyncAdapt_asynch_dbapi(FakeAsynch)
    with patch.object(dbapi.asynch.connection, "Connection") as mock_conn_cls:
        dbapi.connect("dsn", settings={"async_insert": 1})
        call_kwargs = mock_conn_cls.call_args.kwargs
        assert call_kwargs["settings"]["join_use_nulls"] == 1
        assert call_kwargs["settings"]["async_insert"] == 1


def test_connect_preserves_explicit_join_use_nulls():
    dbapi = AsyncAdapt_asynch_dbapi(FakeAsynch)
    with patch.object(dbapi.asynch.connection, "Connection") as mock_conn_cls:
        dbapi.connect("dsn", settings={"join_use_nulls": 0})
        call_kwargs = mock_conn_cls.call_args.kwargs
        assert call_kwargs["settings"]["join_use_nulls"] == 0


# The tests above prove the kwarg reaches the driver. They cannot tell whether
# the setting does anything, because they never talk to a server. The tests
# below run the join that motivated the default and read the row back.

MATCHED_ID = 1
UNMATCHED_ID = 2
SEEN_AT = datetime(2026, 1, 1, 0, 0, 0, 500000)
SEEN_AT_TYPE = "DateTime64(3)"

LEFT_JOIN = """
    SELECT
        l.id AS id,
        r.amount AS amount,
        r.seen_at AS seen_at
    FROM {left} AS l
    LEFT JOIN {right} AS r ON l.id = r.id
    ORDER BY l.id
"""


async def _type_default(conn, type_name):
    """Read a column type's default value back from the server.

    ClickHouse renders a ``DateTime64`` default in the server's own timezone
    and the driver parses it as a naive value, so a server that is not on UTC
    hands back something other than midnight. Asking the same connection for
    the same type's default keeps the expectation tied to the server the test
    is talking to, instead of to a constant that only holds on a UTC server.
    """

    row = (
        await conn.execute(
            text("SELECT defaultValueOfTypeName(:type_name)"),
            {"type_name": type_name},
        )
    ).one()
    return row[0]


async def _seed(conn, left, right):
    await conn.execute(
        text(
            f"""
            CREATE TABLE {left} (
                id UInt64,
                name String
            )
            ENGINE = MergeTree
            ORDER BY id
            """
        )
    )
    await conn.execute(
        text(
            f"""
            CREATE TABLE {right} (
                id UInt64,
                amount UInt32,
                seen_at {SEEN_AT_TYPE}
            )
            ENGINE = MergeTree
            ORDER BY id
            """
        )
    )

    await _execute_each(
        conn,
        text(f"INSERT INTO {left} (id, name) VALUES (:id, :name)"),
        [
            {"id": MATCHED_ID, "name": "has a counterpart"},
            {"id": UNMATCHED_ID, "name": "has none"},
        ],
    )
    await _execute_each(
        conn,
        text(
            f"""
            INSERT INTO {right} (id, amount, seen_at)
            VALUES (:id, :amount, :seen_at)
            """
        ),
        {"id": MATCHED_ID, "amount": 7, "seen_at": SEEN_AT},
    )


@pytest.mark.asyncio
async def test_unmatched_left_join_row_reads_back_as_null():
    """A row that matched nothing comes back as NULL on a default connection.

    This is the contract the ORM depends on: it decides a relationship is
    absent by looking for NULL. The dialect asks for join_use_nulls=1 to get
    it, and this test fails if the request ever stops taking effect.
    """

    left = _table_name("join_use_nulls_left")
    right = _table_name("join_use_nulls_right")
    engine = _engine()

    try:
        async with engine.begin() as conn:
            await _seed(conn, left, right)

            rows = (
                await conn.execute(
                    text(LEFT_JOIN.format(left=left, right=right))
                )
            ).all()

            matched, unmatched = rows

            assert matched.id == MATCHED_ID
            assert matched.amount == 7
            assert matched.seen_at == SEEN_AT

            assert unmatched.id == UNMATCHED_ID
            assert unmatched.amount is None
            assert unmatched.seen_at is None
    finally:
        await _drop(engine, left)
        await _drop(engine, right)
        await engine.dispose()


@pytest.mark.asyncio
async def test_unmatched_left_join_row_reads_back_as_type_default_when_off():
    """Opting out brings back the behaviour the default exists to avoid.

    ClickHouse fills an unmatched column with the column type's default, so a
    missing row is indistinguishable from a real zero and a real epoch
    timestamp. Asserting that here keeps the test above honest: it shows the
    NULLs come from the setting rather than from ClickHouse always sending
    NULL.
    """

    left = _table_name("join_use_nulls_left")
    right = _table_name("join_use_nulls_right")
    engine = _engine({"join_use_nulls": 0})

    try:
        async with engine.begin() as conn:
            await _seed(conn, left, right)

            rows = (
                await conn.execute(
                    text(LEFT_JOIN.format(left=left, right=right))
                )
            ).all()

            unmatched = rows[1]

            assert unmatched.id == UNMATCHED_ID
            assert unmatched.amount == 0
            assert unmatched.seen_at == await _type_default(conn, SEEN_AT_TYPE)
    finally:
        await _drop(engine, left)
        await _drop(engine, right)
        await engine.dispose()
