# Issue #359 Add support for BFloat16

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/359
- Category: 我们可以跟进修复
- Priority: low
- Created: 2025-01-08T00:33:22Z
- Updated: 2025-01-08T00:33:22Z
- Author: franz101
- Labels: none
- Comments: 0

## 判断
BFloat16 类型缺失。

## 本地 fork 现状
types/common.py 与 ischema_names 未包含 BFloat16。

## 建议动作
添加 BFloat16 类型编译、反射和测试。

## Issue 摘要
With Clickhouse 24.12 BFloat16 is out of experimental...
