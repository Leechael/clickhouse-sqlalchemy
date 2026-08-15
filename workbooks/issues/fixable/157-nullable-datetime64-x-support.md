# Issue #157 Nullable DateTime64(x) support

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/157
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2021-12-08T11:43:42Z
- Updated: 2022-08-08T09:58:25Z
- Author: Trokul
- Labels: feature request
- Comments: 1

## 判断
Nullable DateTime64 支持，本地类型和 Alembic render 已有覆盖。

## 本地 fork 现状
types.Nullable(types.DateTime64(...)) 支持，tests/alembic/test_render_types.py 覆盖 Nullable。

## 建议动作
补 round-trip/reflection 专项或标为已修。

## Issue 摘要
**Describe the bug** ClickHouseDialect._get_column_type does not support Nullable(DateTime64(x)) **Expected behavior** Nullable nested_type should be DateTime64
