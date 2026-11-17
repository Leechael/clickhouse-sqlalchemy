# Issue #402 Consider making driver dependencies extras

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/402
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2026-03-18T02:11:47Z
- Updated: 2026-03-18T02:11:47Z
- Author: sk-
- Labels: none
- Comments: 0

## 判断
可做包装结构调整：把 http/native/asynch driver 依赖拆成 extras，同时保留兼容安装策略。

## 本地 fork 现状
当前 pyproject 仍把 requests、clickhouse-driver、Leechael/asynch fork 放在核心 dependencies。

## 建议动作
设计 extras：clickhouse-sqlalchemy[http]、[native]、[asynch]，再决定默认安装是否保留 all。

## Issue 摘要
Currently when installing `clickhouse-sqlalchemy` one gets the following transitive dependencies: - asynch: for asynch driver - clickhouse-driver: for native driver - requests: for http driver This is understandable to provide a good out of the box experience for all users, however it comes with a baggage of bringing lots of extra dependencies, as one will typically use just one driver. ``` ├── clickhouse-sqlalchemy ...
