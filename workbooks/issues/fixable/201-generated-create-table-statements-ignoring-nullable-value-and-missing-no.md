# Issue #201 Generated CREATE TABLE statements ignoring nullable value and missing "NOT NULL" modifier

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/201
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2022-10-03T15:59:37Z
- Updated: 2022-10-03T16:09:38Z
- Author: georgipeev
- Labels: none
- Comments: 0

## 判断
CREATE TABLE 忽略 nullable=False/NOT NULL，影响 DDL 正确性。

## 本地 fork 现状
ClickHouse Nullable 类型由显式 types.Nullable 控制；SQLAlchemy nullable 标志可能未映射。

## 建议动作
决定是否让 Column(nullable=True/False) 自动包装 Nullable，并补 DDL tests。

## Issue 摘要
The documentation of `sqlalchemy.sql.schema.Column` specifies that the `nullable` constructor parameter should affect CREATE TABLE statements (and only them): ``` :param nullable: When set to ``False``, will cause the "NOT NULL" phrase to be added when generating DDL for the column. When ``True``, will normally generate nothing (in SQL this defaults to ``` However, the value of the parameter is explicitly overriden t...
