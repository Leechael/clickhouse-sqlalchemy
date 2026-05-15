from alembic.autogenerate import render
from alembic.autogenerate import renderers
from alembic.operations import ops
from sqlalchemy.sql import elements
from sqlalchemy import schema as sa_schema

from clickhouse_sqlalchemy import engines
from . import operations

indent = ' ' * 4

_render_create_table = renderers.dispatch(ops.CreateTableOp)


def escape(x):
    return x.replace("'", "\\'")


def _render_expression(expr, autogen_context):
    if expr is None:
        return None

    if isinstance(expr, sa_schema.Column):
        return repr(expr.name)

    if isinstance(expr, str):
        return repr(expr)

    if isinstance(expr, (list, tuple)):
        values = [_render_expression(value, autogen_context) for value in expr]
        if len(values) == 1:
            return values[0]
        return '(' + ', '.join(values) + ',)'

    if isinstance(expr, elements.ClauseElement):
        return render._render_potential_expr(expr, autogen_context)

    return repr(expr)


def _render_engine_arg(expr, autogen_context):
    if expr is None:
        return None

    values = getattr(expr, 'expressions', None)
    if values is None:
        values = getattr(expr, 'columns', None)
    if values is None:
        return _render_expression(expr, autogen_context)

    values = list(values)
    rendered = ', '.join(
        _render_expression(value, autogen_context) for value in values
    )
    if len(values) == 1:
        return rendered
    return '(' + rendered + ',)'


def _render_table_col(table_col, autogen_context):
    if table_col is None:
        return None
    return _render_expression(table_col.get_column(), autogen_context)


def _render_engine_params(engine, autogen_context):
    params = []

    if isinstance(engine, engines.GraphiteMergeTree):
        params.append(repr(engine.config_name))

    if isinstance(engine, (
            engines.ReplicatedMergeTree,
            engines.ReplicatedAggregatingMergeTree,
            engines.ReplicatedCollapsingMergeTree,
            engines.ReplicatedVersionedCollapsingMergeTree,
            engines.ReplicatedReplacingMergeTree,
            engines.ReplicatedSummingMergeTree
    )):
        params.extend([repr(engine.table_path), repr(engine.replica_name)])

    if isinstance(engine, (
            engines.CollapsingMergeTree, engines.ReplicatedCollapsingMergeTree
    )):
        params.append(_render_table_col(engine.sign_col, autogen_context))

    if isinstance(engine, (
            engines.VersionedCollapsingMergeTree,
            engines.ReplicatedVersionedCollapsingMergeTree
    )):
        params.extend([
            _render_table_col(engine.sign_col, autogen_context),
            _render_table_col(engine.version_col, autogen_context)
        ])

    return params


def _render_engine(engine, autogen_context):
    if engine is None:
        return None

    cls = engine.__class__
    prefix = 'clickhouse_sqlalchemy.engines.'

    if isinstance(engine, engines.MergeTree):
        args = _render_engine_params(engine, autogen_context)

        if isinstance(engine, (
                engines.ReplacingMergeTree,
                engines.ReplicatedReplacingMergeTree
        )):
            value = _render_table_col(engine.version_col, autogen_context)
            if value is not None:
                args.append('version={}'.format(value))

        if isinstance(engine, (
                engines.SummingMergeTree,
                engines.ReplicatedSummingMergeTree
        )):
            value = _render_engine_arg(engine.summing_cols, autogen_context)
            if value is not None:
                args.append('columns={}'.format(value))

        for name in (
                'partition_by', 'order_by', 'primary_key', 'sample_by', 'ttl'
        ):
            value = _render_engine_arg(
                getattr(engine, name, None), autogen_context
            )
            if value is not None:
                args.append('{}={}'.format(name, value))
        args.extend(
            '{}={!r}'.format(key, value)
            for key, value in sorted(engine.settings.items())
        )
        return '{}{}({})'.format(prefix, cls.__name__, ', '.join(args))

    if isinstance(engine, engines.Distributed):
        args = [
            repr(engine.logs),
            repr(engine.default),
            repr(engine.hits)
        ]
        if engine.sharding_key is not None:
            args.append(_render_expression(engine.sharding_key, autogen_context))
        return '{}{}({})'.format(prefix, cls.__name__, ', '.join(args))

    if isinstance(engine, engines.Buffer):
        args = [
            repr(engine.database),
            repr(engine.table_name),
            repr(engine.num_layers),
            repr(engine.min_time),
            repr(engine.max_time),
            repr(engine.min_rows),
            repr(engine.max_rows),
            repr(engine.min_bytes),
            repr(engine.max_bytes)
        ]
        return '{}{}({})'.format(prefix, cls.__name__, ', '.join(args))

    if isinstance(engine, engines.File):
        return '{}{}({!r})'.format(prefix, cls.__name__, engine.data_format)

    return '{}{}()'.format(prefix, cls.__name__)


def _find_source_table(op):
    metadata = getattr(op, '_namespace_metadata', None)
    if metadata is None:
        return None

    key = sa_schema._get_table_key(op.table_name, op.schema)
    return metadata.tables.get(key)


@renderers.dispatch_for(ops.CreateTableOp, replace=True)
def render_create_table(autogen_context, op):
    if autogen_context.dialect.name != 'clickhouse':
        return _render_create_table(autogen_context, op)

    source_table = _find_source_table(op)
    engine = getattr(source_table, 'engine', None)
    rendered_engine = _render_engine(engine, autogen_context)

    if rendered_engine is None:
        return _render_create_table(autogen_context, op)

    table = op.to_table()
    args = [
        col
        for col in [
            render._render_column(col, autogen_context)
            for col in table.columns
        ]
        if col
    ] + sorted(
        [
            rcons
            for rcons in [
                render._render_constraint(
                    cons, autogen_context, op._namespace_metadata
                )
                for cons in table.constraints
            ]
            if rcons is not None
        ]
    ) + [rendered_engine]

    if len(args) > render.MAX_PYTHON_ARGS:
        args_str = "*[" + ",\n".join(args) + "]"
    else:
        args_str = ",\n".join(args)

    text = "%(prefix)screate_table(%(tablename)r,\n%(args)s" % {
        "tablename": render._ident(op.table_name),
        "prefix": render._alembic_autogenerate_prefix(autogen_context),
        "args": args_str,
    }
    if op.schema:
        text += ",\nschema=%r" % render._ident(op.schema)

    comment = table.comment
    if comment:
        text += ",\ncomment=%r" % render._ident(comment)

    info = table.info
    if info:
        text += f",\ninfo={info!r}"

    for key in sorted(op.kw):
        text += ",\n%s=%r" % (key.replace(" ", "_"), op.kw[key])

    if table._prefixes:
        prefixes = ", ".join("'%s'" % prefix for prefix in table._prefixes)
        text += ",\nprefixes=[%s]" % prefixes

    if op.if_not_exists is not None:
        text += ",\nif_not_exists=%r" % bool(op.if_not_exists)

    text += "\n)"
    return text


@renderers.dispatch_for(operations.CreateMatViewOp)
def render_create_mat_view(autogen_context, op):
    columns = [
        col
        for col in [
            render._render_column(col, autogen_context) for col in op.columns
        ]
        if col
    ]

    templ = (
        "{prefix}create_mat_view(\n"
        "{indent}'{name}',\n"
        "{indent}'{selectable}',\n"
        "{indent}'{engine}',\n"
        "{indent}{columns}\n"
        ")"
    )

    join_indent = ("'\n" + indent + "'")
    return templ.format(
        prefix=render._alembic_autogenerate_prefix(autogen_context),
        name=op.name,
        selectable=join_indent.join(escape(op.selectable).split('\n')),
        engine=join_indent.join(escape(op.engine.strip()).split('\n')),
        columns=(',\n' + indent).join(str(arg) for arg in columns),
        indent=indent
    )


@renderers.dispatch_for(operations.DropMatViewOp)
def render_drop_mat_view(autogen_context, op):
    return (
        render._alembic_autogenerate_prefix(autogen_context) +
        "drop_mat_view('" + op.name + "')"
    )


@renderers.dispatch_for(operations.CreateMatViewToTableOp)
def render_create_mat_view_to_table(autogen_context, op):
    templ = (
        "{prefix}create_mat_view_to_table(\n"
        "{indent}'{name}',\n"
        "{indent}'{selectable}',\n"
        "{indent}'{inner_name}'\n"
        ")"
    )

    join_indent = ("'\n" + indent + "'")
    return templ.format(
        prefix=render._alembic_autogenerate_prefix(autogen_context),
        name=op.name,
        selectable=join_indent.join(escape(op.selectable).split('\n')),
        inner_name=op.inner_name,
        indent=indent
    )


@renderers.dispatch_for(operations.DropMatViewToTableOp)
def render_drop_mat_view_to_table(autogen_context, op):
    return (
        render._alembic_autogenerate_prefix(autogen_context) +
        "drop_mat_view_to_table('" + op.name + "')"
    )


@renderers.dispatch_for(operations.AttachMatViewOp)
def render_attach_mat_view(autogen_context, op):
    columns = [
        col
        for col in [
            render._render_column(col, autogen_context) for col in op.columns
        ]
        if col
    ]

    templ = (
        "{prefix}attach_mat_view(\n"
        "{indent}'{name}',\n"
        "{indent}'{selectable}',\n"
        "{indent}'{engine}',\n"
        "{indent}{columns}\n"
        ")"
    )

    join_indent = ("'\n" + indent + "'")
    return templ.format(
        prefix=render._alembic_autogenerate_prefix(autogen_context),
        name=op.name,
        selectable=join_indent.join(escape(op.selectable).split('\n')),
        engine=join_indent.join(escape(op.engine.strip()).split('\n')),
        columns=(',\n' + indent).join(str(arg) for arg in columns),
        indent=indent
    )


@renderers.dispatch_for(operations.DetachMatViewOp)
def render_detach_mat_view(autogen_context, op):
    return (
        render._alembic_autogenerate_prefix(autogen_context) +
        "detach_mat_view('" + op.name + "')"
    )
