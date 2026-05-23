import asynch

from sqlalchemy.sql.elements import TextClause
from sqlalchemy.pool import AsyncAdaptedQueuePool

from .connector import AsyncAdapt_asynch_dbapi
from ..native.base import (
    ClickHouseDialect_native, ClickHouseExecutionContext,
    ClickHouseNativeSQLCompiler,
)

# Export connector version
VERSION = (0, 0, 1, None)


class ClickHouseAsynchExecutionContext(ClickHouseExecutionContext):
    def create_server_side_cursor(self):
        return self.create_default_cursor()


class ClickHouseAsynchSQLCompiler(ClickHouseNativeSQLCompiler):
    def visit_bindparam(self, bindparam, **kw):
        if not self.isinsert and not kw.get('literal_binds'):
            kw['literal_execute'] = True
        return super(ClickHouseAsynchSQLCompiler, self).visit_bindparam(
            bindparam, **kw
        )


class ClickHouseDialect_asynch(ClickHouseDialect_native):
    driver = 'asynch'
    execution_ctx_cls = ClickHouseAsynchExecutionContext
    statement_compiler = ClickHouseAsynchSQLCompiler

    is_async = True
    supports_statement_cache = True
    supports_server_side_cursors = True

    @classmethod
    def import_dbapi(cls):
        return AsyncAdapt_asynch_dbapi(asynch)

    @classmethod
    def get_pool_class(cls, url):
        return AsyncAdaptedQueuePool

    def _execute(self, connection, sql, scalar=False, **kwargs):
        if isinstance(sql, str):
            # Makes sure the query will go through the
            # `ClickHouseExecutionContext` logic.
            sql = TextClause(sql)
        f = connection.scalar if scalar else connection.execute
        return f(sql, kwargs)

    def do_execute(self, cursor, statement, parameters, context=None):
        # Intercept SET flatten_nested and expand dict-style Nested
        # payloads before the asynch driver sees them.
        self._remember_flatten_nested_setting(statement, cursor)
        statement, parameters = self._prepare_flattened_nested_insert(
            statement, parameters, context, cursor
        )
        cursor.execute(statement, parameters, context)

    def do_executemany(self, cursor, statement, parameters, context=None):
        # Expand dict-style Nested payloads before the asynch driver sees
        # them.  The VALUES template is stripped separately in the cursor
        # wrapper because asynch builds value rows itself.
        statement, parameters = self._prepare_flattened_nested_insert(
            statement, parameters, context, cursor
        )
        cursor.executemany(statement, parameters, context)


dialect = ClickHouseDialect_asynch
