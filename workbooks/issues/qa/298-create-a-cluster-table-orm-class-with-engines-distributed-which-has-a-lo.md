# Issue #298 Create a cluster table orm class with engines.Distributed which has a logs attribute, how to use variable to indicate it?

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/298
- Category: 问答
- Priority: low
- Created: 2024-03-12T02:09:45Z
- Updated: 2024-03-13T09:26:59Z
- Author: flyly0755
- Labels: none
- Comments: 0

## 判断
Distributed engine logs 属性如何变量化是用法问题。

## 本地 fork 现状
engines.Distributed 需要查看具体构造签名；更像建模示例。

## 建议动作
回复如何传 Python 变量/Column/text，必要时补 docs。

## Issue 摘要
For example, one cluster table orm class as below: ```python from clickhouse_sqlalchemy.ext.declarative import declarative_base from clickhouse_sqlalchemy import engines ChBase = declarative_base() class TableXXXCluster(ChBase): # some filed attributes __tablename__ = 'TableXXXCluster' __table_args__ = ( engines.Distributed(logs='cluster', default='currentDatabase()', hits='TableXXX', sharding_key='fieldint'), {'comm...
