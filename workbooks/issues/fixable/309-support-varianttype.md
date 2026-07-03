# Issue #309 Support VariantType

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/309
- Category: 我们可以跟进修复
- Priority: low
- Created: 2024-05-06T23:13:02Z
- Updated: 2024-05-06T23:13:02Z
- Author: franz101
- Labels: none
- Comments: 0

## 判断
Variant 类型缺失。

## 本地 fork 现状
当前 ischema_names/types 未包含 Variant。

## 建议动作
添加 Variant 类型编译/反射，明确 Python 映射。

## Issue 摘要
This powerful column supports multiple formats: https://clickhouse.com/docs/en/sql-reference/data-types/variant#jsonextract-functions-with-variant What would be a workaround if it will not merged soon. text("Variant") obviously will not work
