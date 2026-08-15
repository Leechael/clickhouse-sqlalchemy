# Issue #319 Sqlalchemy can't catch asynch's error

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/319
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-07-04T04:47:35Z
- Updated: 2024-07-04T04:47:35Z
- Author: Simon-Chenzw
- Labels: none
- Comments: 0

## 判断
SQLAlchemy 不能捕获 asynch 错误，可能是 DBAPI exception 映射不完整。

## 本地 fork 现状
AsyncAdapt_asynch_dbapi 动态映射多个 asynch.errors，但未确认 SQLAlchemy Error 继承层级。

## 建议动作
补错误包装/异常层级测试，确保 sqlalchemy.exc 能按预期捕获。

## Issue 摘要
**Describe the bug** I'm trying to catch the asynch exception which raised in pre_ping According to [sqlalchemy's Doc](https://docs.sqlalchemy.org/en/20/core/events.html#sqlalchemy.events.DialectEvents.handle_error) This should be working, but it isn't. ```python def handle_error(e: sa.engine.ExceptionContext): if isinstance(e.original_exception, asynch.errors.UnexpectedPacketFromServerError): raise sqlalchemy.exc.In...
