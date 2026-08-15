# Issue #54 can't use raw sql with http driver

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/54
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2019-03-21T21:37:18Z
- Updated: 2019-09-06T11:01:18Z
- Author: antonio-antuan
- Labels: none
- Comments: 1

## 判断
HTTP raw SQL 缺 format 导致 StopIteration；本地已强制 default_format。

## 本地 fork 现状
RequestsTransport.__init__ 设置 default_format=TabSeparatedWithNamesAndTypes，并 execute 捕获空结果 StopIteration。

## 建议动作
跑 HTTP raw SQL test；可标为已修。

## Issue 摘要
If I call any query using http-session and `execute` method, got that traceback: ``` File "/home/anton/Projects/clickhouse-sqlalchemy/tests/sql/test_schema.py", line 51, in test_reflect session.execute(text('select 1')) File "/home/anton/Projects/venvs/clickhouse-sqlalchemy/lib/python3.7/site-packages/SQLAlchemy-1.3.0b1-py3.7-linux-x86_64.egg/sqlalchemy/orm/session.py", line 1187, in execute bind, close_with_result=T...
