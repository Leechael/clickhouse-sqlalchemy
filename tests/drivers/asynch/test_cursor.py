import asynch
import pytest
from sqlalchemy import event, exc, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.util.concurrency import greenlet_spawn

from clickhouse_sqlalchemy.drivers.asynch.connector import (
    AsyncAdapt_asynch_cursor,
)
from tests.config import system_asynch_uri
from tests.testcase import AsynchSessionTestCase


class CursorTestCase(AsynchSessionTestCase):
    async def test_execute_without_context(self):
        raw = await self.session.bind.raw_connection()
        cur = await greenlet_spawn(lambda: raw.cursor())

        await greenlet_spawn(
            lambda: cur.execute('SELECT * FROM system.numbers LIMIT 1')
        )
        rv = cur.fetchall()

        self.assertEqual(len(rv), 1)

        raw.close()

    async def test_execute_with_context(self):
        rv = await self.session.execute(
            text('SELECT * FROM system.numbers LIMIT 1')
        )

        self.assertEqual(len(rv.fetchall()), 1)

    async def test_check_iter_cursor(self):
        rv = await self.session.execute(
            text('SELECT number FROM system.numbers LIMIT 5')
        )

        self.assertListEqual(list(rv), [(x,) for x in range(5)])

    async def test_execute_with_stream(self):
        async with self.connection.stream(
            text("SELECT * FROM system.numbers LIMIT 10"),
            execution_options={'max_block_size': 1}
        ) as result:
            idx = 0
            async for r in result:
                self.assertEqual(r[0], idx)
                idx += 1

        self.assertEqual(idx, 10)


@pytest.mark.asyncio
async def test_network_error_is_wrapped_and_invalidates_pool(monkeypatch):
    engine = create_async_engine(
        system_asynch_uri,
        pool_size=1,
        max_overflow=0,
    )
    invalidated = []
    event.listen(
        engine.sync_engine.pool,
        'invalidate',
        lambda dbapi_connection, connection_record, exception:
        invalidated.append(exception),
    )
    original_execute = AsyncAdapt_asynch_cursor.execute

    def fail_query(self, operation, params=None, context=None):
        if operation == 'SELECT 1':
            raise asynch.errors.NetworkError('connection lost')
        return original_execute(self, operation, params, context)

    monkeypatch.setattr(AsyncAdapt_asynch_cursor, 'execute', fail_query)
    try:
        async with engine.connect() as connection:
            with pytest.raises(exc.OperationalError) as exc_info:
                await connection.execute(text('SELECT 1'))

        assert exc_info.value.connection_invalidated is True
        assert invalidated
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_pool_pre_ping_replaces_network_disconnected_connection(
        monkeypatch,
):
    engine = create_async_engine(
        system_asynch_uri,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
    )
    original_execute = AsyncAdapt_asynch_cursor.execute
    failed_ping = False

    def fail_first_ping(self, operation, params=None, context=None):
        nonlocal failed_ping
        if operation == 'SELECT 1' and not failed_ping:
            failed_ping = True
            raise asynch.errors.NetworkError('connection lost')
        return original_execute(self, operation, params, context)

    try:
        async with engine.connect() as connection:
            assert (await connection.execute(text('SELECT 42'))).scalar() == 42

        monkeypatch.setattr(
            AsyncAdapt_asynch_cursor,
            'execute',
            fail_first_ping,
        )
        async with engine.connect() as connection:
            assert (await connection.execute(text('SELECT 42'))).scalar() == 42

        assert failed_ping is True
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_engine_dispose_closes_asynch_connection():
    engine = create_async_engine(
        system_asynch_uri,
        pool_size=1,
        max_overflow=0,
    )
    try:
        async with engine.connect() as connection:
            raw_connection = await connection.get_raw_connection()
            driver_connection = raw_connection.driver_connection
            await connection.execute(text('SELECT 42'))
            assert driver_connection._connection.connected is True

        await engine.dispose()
        assert driver_connection._connection.connected is False
    finally:
        await engine.dispose()
