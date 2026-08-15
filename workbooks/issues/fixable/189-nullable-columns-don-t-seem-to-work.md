# Issue #189 Nullable columns don't seem to work

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/189
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2022-08-08T10:07:49Z
- Updated: 2024-03-12T22:51:33Z
- Author: danielgafni
- Labels: none
- Comments: 2

## 判断
Nullable columns 不工作可能涉及 SQLAlchemy nullable 标志和 types.Nullable 语义。

## 本地 fork 现状
当前 Nullable 是显式类型；Column(nullable=True) 不等价。

## 建议动作
文档明确或实现自动 Nullable 映射，需慎重。

## Issue 摘要
**Describe the bug** Nullable columns don't work with: - String - Integer - Enum Passing `None` with any of these types (I didn't check the others) and doing `session.add(); session.commit()` causes an error like: `Enum`: ``` ValueError: None is not a valid Enum8 clickhouse_sqlalchemy.exceptions.DatabaseException: Orig exception: Code: 49. Unknown element 'None' for type Enum8('error' = 0, 'wrong_query' = 1) ``` `Int...
