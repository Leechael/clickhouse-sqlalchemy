import inspect

import pytest

from clickhouse_sqlalchemy.drivers.asynch.connector import AsyncAdapt_asynch_cursor


class _DummyCursor:
    def __init__(self):
        self.closed_calls = 0

    async def close(self):
        self.closed_calls += 1


@pytest.mark.asyncio
async def test_async_soft_close_exists_and_closes_cursor():
    assert inspect.iscoroutinefunction(AsyncAdapt_asynch_cursor._async_soft_close)

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
