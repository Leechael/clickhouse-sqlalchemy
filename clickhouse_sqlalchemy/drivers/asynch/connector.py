import asyncio
import inspect
import re
from datetime import date, datetime
from enum import Enum
from uuid import UUID

from sqlalchemy.engine.interfaces import AdaptedConnection
from sqlalchemy.util.concurrency import await_only
from asynch.proto.utils.escape import escape_chars_map, string_types, text_type


_pyformat_re = re.compile(r'%\(([^)]+)\)s')


def _escape_param(item):
    """Serialize a Python value into a ClickHouse SQL literal string.

    The asynch driver advertises ``paramstyle='pyformat'``, but its
    native parameter binder does not handle complex types (Nested arrays,
    tuples, UUIDs, Enums) correctly.  Before we hand the statement to
    asynch we inline the bound parameters as CH literals so the server
    sees fully materialised values.

    This is intentionally the inverse of a normal parameter-escaping
    layer: it produces SQL text, not a bound value.
    """
    if item is None:
        return "NULL"
    elif isinstance(item, datetime):
        if item.microsecond:
            return "'%s'" % item.strftime("%Y-%m-%d %H:%M:%S.%f")
        return "'%s'" % item.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(item, date):
        return "'%s'" % item.strftime("%Y-%m-%d")
    elif isinstance(item, string_types):
        return "'%s'" % "".join(escape_chars_map.get(c, c) for c in item)
    elif isinstance(item, list):
        return "[%s]" % ", ".join(text_type(_escape_param(x)) for x in item)
    elif isinstance(item, tuple):
        return "(%s)" % ", ".join(text_type(_escape_param(x)) for x in item)
    elif isinstance(item, Enum):
        return _escape_param(item.value)
    elif isinstance(item, UUID):
        return "'%s'" % str(item)
    else:
        return str(item)


def _substitute_pyformat_params(operation, params):
    """Inline dict-style pyformat parameters as CH literals for ``execute()``.

    Replaces ``%(name)s`` placeholders in *operation* with the
    corresponding ClickHouse-literal produced by `_escape_param`.
    Returns the modified SQL and ``None`` for *params* so the asynch
    driver does not attempt its own (broken) binding.
    """
    if not isinstance(params, dict) or not _pyformat_re.search(operation):
        return operation, params

    escaped = {key: _escape_param(value) for key, value in params.items()}

    def replace(match):
        key = match.group(1)
        return escaped[key]

    return _pyformat_re.sub(replace, operation), None


def _strip_pyformat_values_template(operation, params):
    """Truncate the VALUES clause template before ``executemany()``.

    The asynch driver builds value tuples internally when given a list
    of parameter dicts.  If we leave the ``VALUES (%(col)s)`` template
    in the statement, asynch tries to bind the list as a single
    parameter and fails.  Stripping everything after ``VALUES`` lets
    asynch generate the value rows itself while still receiving the
    column list from the preceding ``INSERT INTO ... (cols)`` part.
    """
    if not isinstance(params, (list, tuple)) or not _pyformat_re.search(
        operation
    ):
        return operation, params

    index = operation.upper().rfind('VALUES')
    if index == -1:
        return operation, params

    return operation[:index + len('VALUES')], params


class AsyncAdapt_asynch_cursor:
    __slots__ = (
        '_adapt_connection',
        '_connection',
        'await_',
        '_cursor',
        '_rows',
        '_soft_closed_memoized',
    )

    def __init__(self, adapt_connection):
        self._adapt_connection = adapt_connection
        self._connection = adapt_connection._connection  # noqa
        self.await_ = adapt_connection.await_

        cursor = self._connection.cursor()

        self._cursor = self.await_(cursor.__aenter__())
        self._rows = []
        self._soft_closed_memoized = {}

    @property
    def _execute_mutex(self):
        return self._adapt_connection._execute_mutex  # noqa

    @property
    def description(self):
        memoized = getattr(self, '_soft_closed_memoized', {})
        if 'description' in memoized:
            return memoized['description']
        return self._cursor.description or None

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def arraysize(self):
        return self._cursor.arraysize

    @arraysize.setter
    def arraysize(self, value):
        self._cursor.arraysize = value

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    def close(self):
        self._rows[:] = []  # noqa
        if getattr(self, '_soft_closed_memoized', {}):
            return
        try:
            self.await_(self._cursor.close())
        except Exception:
            pass

    async def _async_soft_close(self) -> None:
        """Soft close for SQLAlchemy 2.0.44+ compatibility.

        This method closes the cursor but keeps the results pending.
        See: https://github.com/sqlalchemy/sqlalchemy/commit/2e9902a
        """
        # NOTE: Do NOT clear _rows here! The purpose of "soft close" is to
        # close the cursor while preserving already-fetched results.
        try:
            close = getattr(self._cursor, "close", None)
            if close is None:
                return
            self._soft_closed_memoized = {
                'description': self._cursor.description or None,
            }
            result = close()
            if inspect.isawaitable(result):
                await result
        except Exception:
            pass

    def execute(self, operation, params=None, context=None):
        return self.await_(self._execute_async(operation, params, context))

    async def _execute_async(self, operation, params, context):
        async with self._execute_mutex:
            operation, params = _substitute_pyformat_params(operation, params)
            result = await self._cursor.execute(
                operation,
                args=params,
                context=context
            )

            description = self.description
            self._rows = []
            if description is not None:
                self._rows = list(await self._cursor.fetchall())
            return result

    def executemany(self, operation, params=None, context=None):
        return self.await_(self._executemany_async(operation, params, context))

    async def _executemany_async(self, operation, params, context):
        async with self._execute_mutex:
            operation, params = _strip_pyformat_values_template(
                operation, params
            )
            return await self._cursor.executemany(
                operation,
                args=params,
                context=context
            )

    def setinputsizes(self, *args):
        pass

    def setoutputsizes(self, *args):
        pass

    def __iter__(self):
        while self._rows:
            yield self._rows.pop(0)

    def fetchone(self):
        if self._rows:
            return self._rows.pop(0)
        else:
            return None

    def fetchmany(self, size=None):
        if size is None:
            size = self.arraysize

        retval = self._rows[0:size]
        self._rows[:] = self._rows[size:]
        return retval

    def fetchall(self):
        retval = self._rows[:]
        self._rows[:] = []
        return retval


class AsyncAdapt_asynch_dbapi:
    def __init__(self, asynch):
        self.asynch = asynch
        self.paramstyle = 'pyformat'
        self._init_dbapi_attributes()

    class Error(Exception):
        pass

    def _init_dbapi_attributes(self):
        for name in (
                'ServerException',
                'UnexpectedPacketFromServerError',
                'LogicalError',
                'UnknownTypeError',
                'ChecksumDoesntMatchError',
                'TypeMismatchError',
                'UnknownCompressionMethod',
                'TooLargeStringSize',
                'NetworkError',
                'SocketTimeoutError',
                'UnknownPacketFromServerError',
                'CannotParseUuidError',
                'CannotParseDomainError',
                'PartiallyConsumedQueryError',
                'ColumnException',
                'ColumnTypeMismatchException',
                'StructPackException',
                'InterfaceError',
                'DatabaseError',
                'ProgrammingError',
                'NotSupportedError',
        ):
            setattr(self, name, getattr(self.asynch.errors, name))

    def connect(self, *args, **kwargs) -> 'AsyncAdapt_asynch_connection':
        settings = kwargs.get('settings', {})
        if 'join_use_nulls' not in settings:
            kwargs = {**kwargs, 'settings': {**settings, 'join_use_nulls': 1}}
        return AsyncAdapt_asynch_connection(
            self,
            self.asynch.connection.Connection(*args, **kwargs)
        )


class AsyncAdapt_asynch_connection(AdaptedConnection):
    await_ = staticmethod(await_only)
    __slots__ = ('dbapi', '_execute_mutex')

    def __init__(self, dbapi, connection):
        self.dbapi = dbapi
        self._connection = connection
        self._execute_mutex = asyncio.Lock()

    def ping(self, reconnect):
        return self.await_(self._ping_async())

    async def _ping_async(self):
        async with self._execute_mutex:
            return await self._connection.ping()

    def character_set_name(self):
        character_set_name = getattr(
            self._connection, 'character_set_name', None
        )
        if character_set_name is None:
            return None

        return character_set_name()

    def autocommit(self, value):
        autocommit = getattr(self._connection, 'autocommit', None)
        if autocommit is None:
            return None

        result = autocommit(value)
        if inspect.isawaitable(result):
            return self.await_(result)
        return result

    def cursor(self, server_side=False):
        return AsyncAdapt_asynch_cursor(self)

    def rollback(self):
        self.await_(self._rollback_async())

    async def _rollback_async(self):
        try:
            result = self._connection.rollback()
            if inspect.isawaitable(result):
                return await result
            return result
        except self.dbapi.NotSupportedError:
            return None

    def commit(self):
        self.await_(self._commit_async())

    async def _commit_async(self):
        try:
            result = self._connection.commit()
            if inspect.isawaitable(result):
                return await result
            return result
        except self.dbapi.NotSupportedError:
            return None

    def close(self):
        result = self._connection.close()
        if inspect.isawaitable(result):
            return self.await_(result)
        return result
