from sqlalchemy import types
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.elements import Label, ColumnClause
from sqlalchemy.sql.type_api import UserDefinedType

from .common import Array


class Nested(types.TypeEngine):
    __visit_name__ = 'nested'

    def __init__(self, *columns):
        if not columns:
            raise ValueError('columns must be specified for nested type')
        self.columns = columns
        self._columns_dict = {col.name: col for col in columns}
        super(Nested, self).__init__()

    def adapt(self, cls, **kw):
        if cls is type(self):
            typ = cls(*self.columns)
            typ._variant_mapping = self._variant_mapping
            return typ

        return super(Nested, self).adapt(cls, **kw)

    def copy(self, **kw):
        return self.adapt(self.__class__)

    class Comparator(UserDefinedType.Comparator):
        def __getattr__(self, key):
            str_key = key.rstrip("_")
            try:
                sub = self.type._columns_dict[str_key]
            except KeyError:
                raise AttributeError(key)
            else:
                original_type = sub.type
                try:
                    sub.type = Array(sub.type)
                    expr = NestedColumn(self.expr, sub)
                    return expr
                finally:
                    sub.type = original_type

    comparator_factory = Comparator


class NestedColumn(ColumnClause):
    inherit_cache = False

    def __init__(self, parent, sub_column):
        self.parent = parent
        self.sub_column = sub_column
        if isinstance(self.parent, Label):
            table = self.parent.element.table
        else:
            table = self.parent.table
        super(NestedColumn, self).__init__(
            sub_column.name,
            sub_column.type,
            _selectable=table
        )


@compiles(NestedColumn)
def _comp(element, compiler, **kw):
    from_labeled_label = False
    if isinstance(element.parent, Label):
        from_labeled_label = True
    return "%s.%s" % (
        compiler.process(element.parent,
                         from_labeled_label=from_labeled_label,
                         within_label_clause=False,
                         within_columns_clause=True),
        compiler.visit_column(element, include_table=False),
    )
