# Issue #282 Bulk update fails on ClickHouse

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/282
- Category: 问答
- Priority: low
- Created: 2024-01-12T11:14:47Z
- Updated: 2024-01-12T11:14:47Z
- Author: vkozmik
- Labels: none
- Comments: 0

## 判断
ClickHouse UPDATE 是 ALTER UPDATE mutation，不支持传统 bulk update 语义。

## 本地 fork 现状
compiler 支持 ALTER UPDATE，但要求 WHERE；批量 ORM update 可能不匹配。

## 建议动作
回复支持边界；若可行，补 SQLAlchemy bulk update 文档/限制。

## Issue 摘要
Bulk update fails through click house driver, at is is detected as insert clickhouse_driver/client.py", line 367, in execute is_insert = isinstance(params, (list, tuple, types.GeneratorType)) Following SQL Alchemy query does not work session.execute(update(Table), [data1, data2]) However single updates work: for data in [data1, data2]: session.execute(update(Table), [data]) clickhouse-sqlalchemy 0.3.0, sqlalchemy 2.0...
