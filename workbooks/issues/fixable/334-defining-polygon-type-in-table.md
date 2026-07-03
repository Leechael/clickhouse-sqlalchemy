# Issue #334 Defining polygon type in table

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/334
- Category: 我们可以跟进修复
- Priority: low
- Created: 2024-09-05T14:19:15Z
- Updated: 2024-09-05T14:19:15Z
- Author: yirmav
- Labels: none
- Comments: 0

## 判断
Polygon/geo 类型定义缺口，和 #252 相关。

## 本地 fork 现状
当前类型只含 IPv4/IPv6，无 Point/Ring/Polygon/MultiPolygon。

## 建议动作
和 missing geo data types 一起实现。

## Issue 摘要
**Describe the bug** Clickhouse supports Polygon type is there any way to utilize this as a minimum when defining our tables ? **Expected behavior** Add support or explain how we can define polygons
