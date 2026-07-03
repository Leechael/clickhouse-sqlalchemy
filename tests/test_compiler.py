import enum
from sqlalchemy import sql, Column, func, literal, literal_column, select, text

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

    def test_render_literal_value_detects_nulltype_by_isinstance_only(self):
        from sqlalchemy.sql.type_api import UserDefinedType
        from clickhouse_sqlalchemy.drivers.base import clickhouse_dialect
        from clickhouse_sqlalchemy.drivers.compilers.sqlcompiler import (
            ClickHouseSQLCompiler,
        )

        class NullColSpecUDT(UserDefinedType):
            __visit_name__ = 'user_defined'

            def get_col_spec(self, **kwargs):
                return 'Null'

            def literal_processor(self, dialect):
                def process(value):
                    return 'CUSTOM_' + str(value)
                return process

        compiler = ClickHouseSQLCompiler(clickhouse_dialect, None)
        custom_type = NullColSpecUDT()

        # str(custom_type).upper() == 'NULL' would be True because
        # get_col_spec returns 'Null'.  The old code would mistakenly
        # re-type to String, bypassing literal_processor.
        result = compiler.render_literal_value('hello', custom_type)
        self.assertEqual(result, 'CUSTOM_hello')


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


class NestedInsertPrefixTestCase(NativeSessionTestCase):
    """Regression: INSERT with Nested columns must preserve CTE WITH
    clauses and prefix_with() hints in the rebuilt SQL."""

    def _nested_table(self):
        return Table(
            't1', self.metadata(),
            Column('x', types.Int32),
            Column('n', types.Nested(
                Column('a', types.Int32),
                Column('b', types.String),
            )),
            engines.Memory()
        )

    def _render_nested(self, stmt):
        dialect = self.session.bind.dialect
        row = {'n.a': [1], 'n.b': ['hello']}
        return dialect._render_flattened_nested_insert(
            self._nested_table(), row, stmt,
            include_values_template=True,
        )

    def test_cte_preserved_with_nested(self):
        """add_cte() WITH clause must appear in the rewritten INSERT."""
        cte = select(text('1')).cte('my_cte')
        stmt = self._nested_table().insert().values(
            n={'a': [1], 'b': ['hello']}
        ).add_cte(cte)

        sql = self._render_nested(stmt)
        self.assertIn('WITH my_cte AS', sql)
        self.assertIn('INSERT', sql)
        self.assertTrue(sql.startswith('WITH'))

    def test_prefix_with_preserved_with_nested(self):
        """prefix_with() hints must appear after INSERT."""
        stmt = self._nested_table().insert().values(
            n={'a': [1], 'b': ['hello']}
        ).prefix_with('SOME_HINT', dialect='*')

        sql = self._render_nested(stmt)
        self.assertIn('INSERT SOME_HINT INTO', sql)

    def test_cte_and_prefix_with_together(self):
        """Both CTE and prefix_with() must work together."""
        cte = select(text('1')).cte('my_cte')
        stmt = self._nested_table().insert().values(
            n={'a': [1], 'b': ['hello']}
        ).add_cte(cte).prefix_with('HINT', dialect='*')

        sql = self._render_nested(stmt)
        self.assertTrue(sql.startswith('WITH'))
        self.assertIn('INSERT HINT INTO', sql)

    def test_multiple_ctes_preserved(self):
        """Multiple CTEs must all appear, comma-separated."""
        cte1 = select(text('1')).cte('first')
        cte2 = select(text('2')).cte('second')
        stmt = self._nested_table().insert().values(
            n={'a': [1], 'b': ['hello']}
        ).add_cte(cte1).add_cte(cte2)

        sql = self._render_nested(stmt)
        self.assertIn('WITH first AS', sql)
        self.assertIn('second AS', sql)
        self.assertIn(', ', sql)  # CTEs are comma-separated

    def test_no_cte_no_prefix_is_clean(self):
        """Without CTE or prefix_with, INSERT must be clean (no regressions)."""
        stmt = self._nested_table().insert().values(
            n={'a': [1], 'b': ['hello']}
        )

        sql = self._render_nested(stmt)
        self.assertEqual(
            sql,
            'INSERT INTO t1 (n.a, n.b) VALUES (%(n.a)s, %(n.b)s)'
        )

    def test_cte_is_preserved_in_compiled_insert(self):
        """Full compilation path must preserve CTE for Nested INSERT."""
        cte = select(text('1')).cte('my_cte')
        stmt = self._nested_table().insert().values(
            n={'a': [1], 'b': ['hello']}
        ).add_cte(cte)

        compiled = self._compile(stmt)
        sql = str(compiled)
        # The standard compiler outputs the CTE.
        self.assertIn('WITH my_cte AS', sql)
