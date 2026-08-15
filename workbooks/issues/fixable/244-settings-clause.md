# Issue #244 SETTINGS clause

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/244
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2023-04-24T15:33:37Z
- Updated: 2023-04-24T20:13:22Z
- Author: Net-Mist
- Labels: none
- Comments: 3

## 判断
SETTINGS clause 支持是可做/可文档化项。

## 本地 fork 现状
drivers connector 已支持 execution_options(settings=...)，HTTP 会拼 SETTINGS。

## 建议动作
确认是否需要 Select.settings() API；可补文档和编译测试。

## Issue 摘要
Hello, Thanks a lot for this great project. I'm using it on a daily basis and works very well. I was wondering if it could be interesting to add a new clause for the [SETTINGS](https://clickhouse.com/docs/en/sql-reference/statements/select#settings-in-select-query). As far as I know it is not provided by sqlalchemy. If yes, I can try to create a pull request for this. Thanks a lot
