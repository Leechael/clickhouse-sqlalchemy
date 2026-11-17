# Issue #396 HTTP driver don't support the boolean type

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/396
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2025-11-21T11:57:40Z
- Updated: 2025-11-21T11:58:10Z
- Author: irtimir
- Labels: none
- Comments: 1

## 判断
HTTP driver 对 Bool/Boolean 结果没有转换器，可能返回字符串。

## 本地 fork 现状
HTTP transport converters 中没有 Bool/Boolean；base reflection 已能识别 Bool。

## 建议动作
给 HTTP transport 增加 Bool/Boolean converter 和测试。

## Issue 摘要
**Describe the bug** If a column has a boolean type, then in Python it becomes a string. **To Reproduce** ```python engine = create_engine('clickhouse+http://...') t = Table( 'table', Column('is_something', Boolean), ) with engine.connect() as conn: query = select(t.c.is_something).select_from(t) result = list(conn.execute(query)) print(result[0][0]) ``` **Expected behavior** `Bool` type is converted to `bool` **Vers...
