# Issue #203 sqlalchemy>=1.4 inspection error on future.Engine use

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/203
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2022-10-05T15:51:39Z
- Updated: 2022-10-07T02:22:34Z
- Author: randomowo
- Labels: none
- Comments: 1

## 判断
SQLAlchemy>=1.4 future.Engine inspection error；本 fork 已转 SQLAlchemy 2，需确认 inspect 路径。

## 本地 fork 现状
pyproject 只支持 SQLAlchemy 2；dialect inspector 存在。

## 建议动作
跑 reflection/inspection 测试；旧 1.4 future.Engine 不再作为目标。

## Issue 摘要
In sqlalchemy>=1.4 usage of raw string value as sql in future Engine and AsyncEngine are deprecated **To Reproduce** ```python from sqlalchemy.future.engine import create_engine from sqlalchemy.engine import URL from sqlalchemy import inspect, text url = URL.create( 'clickhouse+native', host='localhost', port=9321, username='default', ) engine = create_engine(url) with engine.connect() as conn: conn.execute( text( 'c...
