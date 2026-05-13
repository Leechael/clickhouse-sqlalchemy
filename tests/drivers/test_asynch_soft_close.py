import asyncio
import inspect
from types import SimpleNamespace

import asynch
import pytest

from clickhouse_sqlalchemy.drivers.asynch.connector import (
    AsyncAdapt_asynch_connection,
    AsyncAdapt_asynch_cursor,
    AsyncAdapt_asynch_dbapi,
)


class _DummyCursor:
    def __init__(self):
        self.closed_calls = 0

    async def close(self):
        self.closed_calls += 1


class _DummyDriverCursor:
    def __init__(self):
        self.executemany_context = None

    async def executemany(self, operation, args=None, context=None):
        self.executemany_context = context
        return len(args)


class _UnsupportedTransactionConnection:
    async def commit(self):
        raise asynch.errors.NotSupportedError

    async def rollback(self):
        raise asynch.errors.NotSupportedError


@pytest.mark.asyncio
async def test_async_soft_close_exists_and_closes_cursor():
    assert inspect.iscoroutinefunction(
        AsyncAdapt_asynch_cursor._async_soft_close
    )

    cursor = AsyncAdapt_asynch_cursor.__new__(AsyncAdapt_asynch_cursor)
    cursor._cursor = _DummyCursor()
    cursor._rows = [("a",), ("b",)]

    await cursor._async_soft_close()

    # _async_soft_close should NOT clear _rows - it's a "soft" close that
    # preserves already-fetched results while closing the cursor
    assert cursor._rows == [("a",), ("b",)]
    assert cursor._cursor.closed_calls == 1


@pytest.mark.asyncio
async def test_async_soft_close_noop_without_close():
    cursor = AsyncAdapt_asynch_cursor.__new__(AsyncAdapt_asynch_cursor)
    cursor._cursor = object()
    cursor._rows = [("a",)]

    await cursor._async_soft_close()

    # _rows should be preserved even when cursor has no close method
    assert cursor._rows == [("a",)]


def test_connect_uses_asynch_connection_constructor():
    dbapi = AsyncAdapt_asynch_dbapi(asynch)

    connection = dbapi.connect(
        'clickhouse://default:@localhost/test',
        settings={'async_insert': 1, 'wait_for_async_insert': 1},
    )

    assert isinstance(connection._connection, asynch.connection.Connection)


@pytest.mark.asyncio
async def test_commit_and_rollback_ignore_not_supported():
    dbapi = AsyncAdapt_asynch_dbapi(asynch)
    connection = AsyncAdapt_asynch_connection(
        dbapi,
        _UnsupportedTransactionConnection(),
    )

    assert await connection._commit_async() is None
    assert await connection._rollback_async() is None


@pytest.mark.asyncio
async def test_executemany_passes_context_to_asynch_cursor():
    driver_cursor = _DummyDriverCursor()
    cursor = AsyncAdapt_asynch_cursor.__new__(AsyncAdapt_asynch_cursor)
    cursor._cursor = driver_cursor
    cursor._adapt_connection = SimpleNamespace(_execute_mutex=asyncio.Lock())
    context = SimpleNamespace(
        execution_options={
            'settings': {
                'async_insert': 1,
                'wait_for_async_insert': 1,
            },
        },
    )

    rowcount = await cursor._executemany_async(
        'INSERT INTO test VALUES',
        [{'x': 1}, {'x': 2}],
        context,
    )

    assert rowcount == 2
    assert driver_cursor.executemany_context is context
