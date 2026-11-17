# Issue #195 Clickhouse alembic array nullable field

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/195
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2022-08-24T13:50:15Z
- Updated: 2022-08-24T21:20:55Z
- Author: tvorogme
- Labels: none
- Comments: 5

## 判断
Alembic array nullable field 渲染/对比问题。

## 本地 fork 现状
alembic render_type 支持 Array(Nullable(...))，已有 tests/alembic 覆盖。

## 建议动作
复现 issue 输入；若已通过则标为已修。

## Issue 摘要
**Describe the bug** ![image](https://user-images.githubusercontent.com/19264196/186435517-aafd586a-15dc-4846-8766-14904adf3f02.png) Auto-generated migration field on array field: ``` op.alter_column('accounts', 'account_state_state_init_code_methods', existing_type=clickhouse_sqlalchemy.types.common.Array(Nullable(<class 'clickhouse_sqlalchemy.types.common.Int64'>)), nullable=True) ``` **To Reproduce** Add array fie...
