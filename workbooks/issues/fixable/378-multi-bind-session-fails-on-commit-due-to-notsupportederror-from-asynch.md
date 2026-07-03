# Issue #378 Multi-bind session fails on commit() due to NotSupportedError from asynch

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/378
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2025-05-29T11:43:53Z
- Updated: 2025-08-29T08:49:35Z
- Author: gaganpreet
- Labels: none
- Comments: 1

## 判断
multi-bind session commit 触发 asynch NotSupportedError，和 #386/#352 同类。

## 本地 fork 现状
本地 commit/rollback 已 no-op 化。

## 建议动作
补 multi-bind async session 回归测试，确认不再抛错。

## Issue 摘要
I ran into an issue with using this package with my multi bind session. I am doing something like this: ``` async_engines = { DatabaseType.POSTGRES: create_async_engine( str(config.ASYNC_DATABASE_URL), **db_engine_params ), DatabaseType.CLICKHOUSE: create_async_engine( str(config.CLICKHOUSE_URL), **db_engine_params, execution_options={"final": True}, ), } SessionMaker = async_sessionmaker( binds={ PostgresBase: self....
