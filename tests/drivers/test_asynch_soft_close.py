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
        self.description = [('x', 'UInt8', None, None, None, None, True)]

    async def close(self):
        self.closed_calls += 1
        self.description = None


class _DummyExecuteCursor:
    def __init__(self, description, rows=(), rowcount=-1):
        self.description = description
        self.rows = list(rows)
        self.rowcount = rowcount
        self.execute_context = None
        self.fetchall_calls = 0
        self.closed_calls = 0

    async def execute(self, operation, args=None, context=None):
        self.operation = operation
        self.args = args
        self.execute_context = context
        return self.rowcount

    async def fetchall(self):
        self.fetchall_calls += 1
        if self.description is None:
            raise AssertionError('fetchall should not be called')
        return self.rows

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
    cursor._soft_closed_memoized = {}

    await cursor._async_soft_close()

    # _async_soft_close should NOT clear _rows - it's a "soft" close that
    # preserves already-fetched results while closing the cursor
    assert cursor._rows == [("a",), ("b",)]
    assert cursor._cursor.closed_calls == 1
    assert cursor.description == [
        ('x', 'UInt8', None, None, None, None, True)
    ]


@pytest.mark.asyncio
async def test_async_soft_close_noop_without_close():
    cursor = AsyncAdapt_asynch_cursor.__new__(AsyncAdapt_asynch_cursor)
    cursor._cursor = object()
    cursor._rows = [("a",)]
    cursor._soft_closed_memoized = {}

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


@pytest.mark.asyncio
async def test_execute_does_not_fetch_without_result_set():
    for no_result_description in (None, []):
        driver_cursor = _DummyExecuteCursor(
            description=no_result_description,
            rowcount=-1,
        )
        cursor = AsyncAdapt_asynch_cursor.__new__(AsyncAdapt_asynch_cursor)
        cursor._cursor = driver_cursor
        cursor._rows = [("stale",)]
        cursor._adapt_connection = SimpleNamespace(_execute_mutex=asyncio.Lock())
        cursor._soft_closed_memoized = {}
        context = SimpleNamespace(execution_options={})

        rowcount = await cursor._execute_async(
            'DROP TABLE IF EXISTS test',
            None,
            context,
        )

        assert rowcount == -1
        assert cursor._rows == []
        assert cursor.description is None
        assert driver_cursor.fetchall_calls == 0
        assert driver_cursor.execute_context is context


@pytest.mark.asyncio
async def test_async_soft_close_normalizes_empty_description():
    driver_cursor = _DummyExecuteCursor(description=[])
    cursor = AsyncAdapt_asynch_cursor.__new__(AsyncAdapt_asynch_cursor)
    cursor._cursor = driver_cursor
    cursor._rows = []
    cursor._soft_closed_memoized = {}

    await cursor._async_soft_close()

    assert cursor.description is None


@pytest.mark.asyncio
async def test_execute_prefetches_when_result_set_available():
    description = [('number', 'UInt64', None, None, None, None, True)]
    driver_cursor = _DummyExecuteCursor(
        description=description,
        rows=[(1,), (2,)],
        rowcount=2,
    )
    cursor = AsyncAdapt_asynch_cursor.__new__(AsyncAdapt_asynch_cursor)
    cursor._cursor = driver_cursor
    cursor._rows = []
    cursor._adapt_connection = SimpleNamespace(_execute_mutex=asyncio.Lock())
    context = SimpleNamespace(execution_options={})

    rowcount = await cursor._execute_async(
        'SELECT number FROM system.numbers LIMIT 2',
        None,
        context,
    )

    assert rowcount == 2
    assert cursor._rows == [(1,), (2,)]
    assert driver_cursor.fetchall_calls == 1
    assert driver_cursor.execute_context is context
