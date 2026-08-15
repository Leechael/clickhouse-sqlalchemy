# Issue #279 Usage with CHDB?

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/279
- Category: 问答
- Priority: low
- Created: 2023-12-20T20:00:29Z
- Updated: 2025-01-26T20:23:19Z
- Author: yunyu
- Labels: none
- Comments: 2

## 判断
CHDB 用法/支持问题，和 #308 同类。

## 本地 fork 现状
没有 chdb driver。

## 建议动作
回复当前不支持，建议使用现有 HTTP/native/asynch 或另开 driver 设计。

## Issue 摘要
**Describe the bug** Is there an easy way to use clickhouse-sqlalchemy with https://github.com/chdb-io/chdb/, for use cases like integration tests? It looks like the only available drivers are `native` `http` or `asynch`. **To Reproduce** Try to connect with `chdb` using the DB-API driver, i.e. `clickhouse+chdb://`. The driver isn't supported **Expected behavior** Sqlalchemy connects with CHDB **Versions** - 0.3.0 - ...
