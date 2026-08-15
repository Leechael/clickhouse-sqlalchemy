# Issue #235 Alembic branching is not supported

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/235
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2023-02-16T13:26:54Z
- Updated: 2023-03-20T08:41:47Z
- Author: MichaelDc86
- Labels: feature request
- Comments: 1

## 判断
Alembic branching 支持缺口。

## 本地 fork 现状
当前 Alembic ops 覆盖 mat views/DDL，但未见 branch-specific 支持。

## 建议动作
复现分支 migration 场景，补 version table/branch labels 测试。

## Issue 摘要
**Describe the bug** When creating for ex 2 alembic branches they are written into alembic_version as 2 lines. but order_by=func.tuple( in ReplacingMergeTree doesn't switch off sorting. After some time or by evaluating Optimize 2 lines in alembic_version become 1. **To Reproduce** Create more than 1 alembic branches, run optimize table alembic_version and look into alembic_version. **Expected behavior** All alembic b...
