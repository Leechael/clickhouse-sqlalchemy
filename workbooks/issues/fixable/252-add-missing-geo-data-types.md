# Issue #252 Add missing geo data types.

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/252
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2023-06-15T14:26:13Z
- Updated: 2025-08-28T15:56:12Z
- Author: gregersn
- Labels: none
- Comments: 1

## 判断
Geo 类型缺失。

## 本地 fork 现状
当前未实现 Point/Ring/Polygon/MultiPolygon。

## 建议动作
添加 geo 类型类、compiler、reflection、docs。

## Issue 摘要
**Describe the bug** Support for Geo Data Types are missing. https://clickhouse.com/docs/en/sql-reference/data-types/geo
