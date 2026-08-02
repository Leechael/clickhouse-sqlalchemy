# Issue #335 Division operator results in an invalid cast

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/335
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-09-06T18:11:58Z
- Updated: 2025-05-15T20:13:16Z
- Author: markalexander
- Labels: none
- Comments: 5

## 判断
除法操作被错误 cast，属于 SQL 编译问题。

## 本地 fork 现状
需要复现具体 SQLAlchemy 表达式；当前 compiler 未见除法特殊处理。

## 建议动作
补除法表达式编译测试，调整类型 coercion/cast 行为。

## Issue 摘要
**Describe the bug** When using the `/` operator on numbers, the denominator gets `CAST` as `Decimal(None, None)`, which has invalid arguments and results in `DB::Exception: Decimal argument precision is invalid`. **To Reproduce** For a simple example: ```python session.query((literal(1) / literal(1))).all() ``` This gives me SQL: ```sql SELECT %(param_1)s / CAST(%(param_2)s AS Decimal(None, None)) AS anon_1 ``` And ...
