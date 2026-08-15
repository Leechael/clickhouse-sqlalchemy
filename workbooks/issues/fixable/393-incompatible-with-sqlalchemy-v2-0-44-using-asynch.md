# Issue #393 Incompatible with Sqlalchemy v2.0.44 using asynch

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/393
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2025-10-17T09:36:33Z
- Updated: 2025-12-24T12:17:34Z
- Author: nils-borrmann-tacto
- Labels: none
- Comments: 8

## 判断
SQLAlchemy 2.0.44 asynch cursor soft-close 兼容问题，本地看起来已处理。

## 本地 fork 现状
AsyncAdapt_asynch_cursor 已实现 _async_soft_close，相关测试文件 tests/drivers/test_asynch_soft_close.py 存在。

## 建议动作
跑对应测试；若通过，可记录为我们 fork 已修。

## Issue 摘要
On Sqlalchemy v2.0.44 I am running into the following error: ``` if is_cursor and cursor_result.cursor is not None: > await cursor_result.cursor._async_soft_close() ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ E AttributeError: 'AsyncAdapt_asynch_cursor' object has no attribute '_async_soft_close' ``` This is caused by this commit in sqlalchemy: https://github.com/sqlalchemy/sqlalchemy/commit/2e9902a34fafff0ac6d6c521a86c7d...
