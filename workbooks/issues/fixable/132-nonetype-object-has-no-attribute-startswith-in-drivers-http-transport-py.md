# Issue #132 'nonetype' object has no attribute 'startswith' in drivers/http/transport.py

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/132
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2021-05-07T12:24:01Z
- Updated: 2023-02-03T07:49:20Z
- Author: geekkun
- Labels: none
- Comments: 5

## 判断
HTTP transport type_str 为 None 时 startswith 崩溃。

## 本地 fork 现状
_get_type 未处理 None。

## 建议动作
补 None/空类型保护和 HTTP 响应解析测试。

## Issue 摘要
https://github.com/xzkostyan/clickhouse-sqlalchemy/blob/71564b5f02f2ac487bb48d475638a2c73f98d612/clickhouse_sqlalchemy/drivers/http/transport.py#L80 I've noticed there is no checking for an incoming None value in def _get_type(type_str) and therefore the library fails.
