# Issue #350 v0.2.x and SQLAlchemy 1.4.x - TypeError: expected bytes, str found

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/350
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-11-08T19:01:33Z
- Updated: 2025-06-16T16:06:38Z
- Author: martingstall-db1
- Labels: none
- Comments: 1

## 判断
v0.2.x/SQLAlchemy 1.4 的 bytes/str 问题可能在本 fork 的 SQLAlchemy 2 迁移后不适用，但需定位原路径。

## 本地 fork 现状
本 fork 不再支持 SQLAlchemy 1.4。

## 建议动作
若仍能在 SQLAlchemy 2 复现则修；否则作为不再支持旧矩阵回复。

## Issue 摘要
Trying to upgrade SQLAlchemy 1.3 to 1.4 and we're getting this error on a previously working query around XX.all() clickhouse-driver==0.2.9 clickhouse-sqlalchemy==0.2.7 /python/lib/python3.9/site-packages/sqlalchemy/engine/result.py:1129: in all return self._allrows() /python/lib/python3.9/site-packages/sqlalchemy/engine/result.py:401: in _allrows rows = self._fetchall_impl() /python/lib/python3.9/site-packages/sqlal...
