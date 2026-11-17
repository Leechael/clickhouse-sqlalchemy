# Issue #308 With chdb this clickhouse downsized memory database, can clickhouse-sqlalchemy support it or not?

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/308
- Category: 问答
- Priority: low
- Created: 2024-04-29T06:19:21Z
- Updated: 2024-04-29T06:19:21Z
- Author: flyly0755
- Labels: none
- Comments: 0

## 判断
CHDB 支持是集成方向问题，不是已有 driver 的直接 bug。

## 本地 fork 现状
当前 entry points 没有 chdb driver。

## 建议动作
回复当前不支持；可单独设计 chdb dialect/driver。

## Issue 摘要
chdb is an embedded SQL OLAP Engine powered by ClickHouse. Only store data in memory intead of disk. https://github.com/chdb-io/chdb chdb supports DB-API 2.0 database process. But doesn't support ORM related function. What I think is whether we can reuse clickhouse-sqlalchemy as a chdb dialect. Maybe need some code development, but can reduce lots of workload compare with constructing a fully new dialect for chdb? ht...
