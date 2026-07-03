import enum
from sqlalchemy import sql, Column, func, literal, literal_column

from clickhouse_sqlalchemy import types, Table, engines
from clickhouse_sqlalchemy.drivers.util import get_pyformat_insert_values_template
from tests.testcase import CompilationTestCase, NativeSessionTestCase


class VisitTestCase(CompilationTestCase):
    def test_true_false(self):
        self.assertEqual(self.compile(sql.false()), 'false')
        self.assertEqual(self.compile(sql.true()), 'true')

    def test_array(self):
        self.assertEqual(
            self.compile(types.Array(types.Int32())),
            'Array(Int32)'
        )
        self.assertEqual(
            self.compile(types.Array(types.Array(types.Int32()))),
            'Array(Array(Int32))'
        )

    def test_enum(self):
        class MyEnum(enum.Enum):
            __order__ = 'foo bar'
            foo = 100
            bar = 500

        self.assertEqual(
            self.compile(types.Enum(MyEnum)),
            "Enum('foo' = 100, 'bar' = 500)"
        )

        self.assertEqual(
            self.compile(types.Enum16(MyEnum)),
            "Enum16('foo' = 100, 'bar' = 500)"
        )

        MyEnum = enum.Enum('MyEnum', [" ' t = ", "test"])

        self.assertEqual(
            self.compile(types.Enum8(MyEnum)),
            "Enum8(' \\' t = ' = 1, 'test' = 2)"
        )

    def test_do_not_allow_execution(self):
        with self.assertRaises(TypeError):
            self.session.execute('SHOW TABLES')

        with self.assertRaises(TypeError):
            self.session.query(literal(0)).all()


class VisitNativeTestCase(NativeSessionTestCase):
    def test_insert_no_templates_after_value(self):
        # Optimized non-templating insert test (native protocol only).
        table = Table(
            't1', self.metadata(),
            Column('x', types.Int32),
            engines.Memory()
        )
        self.assertEqual(
            self.compile(table.insert()),
            'INSERT INTO t1 (x) VALUES'
        )

    def test_insert_inplace_values(self):
        table = Table(
            't1', self.metadata(),
            Column('x', types.Int32),
            engines.Memory()
        )
        self.assertEqual(
            self.compile(
                table.insert().values(x=literal_column(str(42))),
                literal_binds=True
            ), 'INSERT INTO t1 (x) VALUES (42)'
        )

    def test_values_template_not_stored_for_mixed_expr_values(self):
        """When .values() mixes SQL expressions with bound parameters,
        the VALUES template must not be stored on the compiled object.
        Otherwise asynch's _executemany_async strips it and loses the
        inline SQL expression, causing KeyError when rebuilding rows."""
        table = Table(
            't1', self.metadata(),
            Column('x', types.Int32),
            Column('y', types.Int32),
            engines.Memory()
        )

        stmt = table.insert().values(x=func.now(), y=42)
        compiled = self._compile(stmt)
        sql = str(compiled)

        # SQL keeps the VALUES clause with inline expressions mixed with
        # pyformat placeholders for plain values.  The regular execute path
        # (not EXECUTEMANY) handles this, binding plain values while
        # passing inline expressions through.
        self.assertIn('now()', sql)
        self.assertIn('%(y)s', sql)

        # The _clickhouse_insert_values_template attribute must NOT be
        # present on the compiled object so that _executemany_async won't
        # try to strip it and pre_exec won't trigger EXECUTEMANY.
        self.assertFalse(
            hasattr(compiled, '_clickhouse_insert_values_template')
        )

    def test_values_template_stored_for_pure_values(self):
        """When .values() has only plain bound parameters (no SQL
        expressions), the pure-pyformat template is stored so that
        asynch can strip and rebuild it correctly."""
        table = Table(
            't1', self.metadata(),
            Column('x', types.Int32),
            Column('y', types.Int32),
            engines.Memory()
        )

        stmt = table.insert().values(x=42, y=43)
        compiled = self._compile(stmt)
        sql = str(compiled)

        # SQL preserves the VALUES template for asynch to rebuild.
        self.assertIn('%(', sql)

        # The stored template must be the pure-pyformat VALUES tuple.
        template = getattr(
            compiled, '_clickhouse_insert_values_template', None
        )
        self.assertEqual(template, '(%(x)s, %(y)s)')
