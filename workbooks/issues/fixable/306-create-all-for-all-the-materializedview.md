# Issue #306 `create_all` for all the `MaterializedView`

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/306
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-03-31T06:26:40Z
- Updated: 2024-03-31T06:26:40Z
- Author: yuvalshi0
- Labels: none
- Comments: 0

## 判断
create_all 对多个 MaterializedView 的处理可改进。

## 本地 fork 现状
项目有 MaterializedView 支持和 Alembic mat view operations。

## 建议动作
复现多 MV create_all 顺序/遗漏问题，补 schema create/drop 测试。

## Issue 摘要
Hi, The [example](https://clickhouse-sqlalchemy.readthedocs.io/en/latest/features.html#materialized-views) in the documentation shows a way to create a materialised view, this however requires a specific call for each materialised view I create. Given that I have a large number of materialised views, how can I create them all in one call? (Like in sqlalchemy `Base.metadata.create_all` for example) Thanks!
