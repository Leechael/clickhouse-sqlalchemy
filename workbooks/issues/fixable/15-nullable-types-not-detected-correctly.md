# Issue #15 Nullable types not detected correctly

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/15
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2018-05-17T09:23:51Z
- Updated: 2019-05-08T11:55:31Z
- Author: AbdealiLoKo
- Labels: none
- Comments: 3

## 判断
HTTP Nullable 类型检测问题，本地已有 Nullable converter 递归处理。

## 本地 fork 现状
transport._get_type 处理 Nullable(...) 并递归 subtype。

## 建议动作
补 Nullable(Float32) HTTP 回归或标为已修。

## Issue 摘要
I have a column with type `Nullable(Float32)`. When I query this value, it gives me a string value as the output for this column. The `converters` at https://github.com/xzkostyan/clickhouse-sqlalchemy/blob/fe2c8b7a9ec4dfe6c872091c8c6ba30bbfe50476/src/drivers/http/transport.py#L10 do not support Nullable types
