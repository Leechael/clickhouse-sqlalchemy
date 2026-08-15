# Issue #330 Table metadata fails to reflect if is_deleted column is set along with version in ReplacingMergeTree engine

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/330
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-08-19T22:28:47Z
- Updated: 2025-01-07T14:34:01Z
- Author: kxd8163
- Labels: none
- Comments: 1

## 判断
ReplacingMergeTree 带 is_deleted 和 version 的反射失败。

## 本地 fork 现状
ReplacingMergeTree.reflect 目前只取一个 version_col，未处理 is_deleted 参数。

## 建议动作
扩展 ReplacingMergeTree 参数解析，覆盖 version,is_deleted。

## Issue 摘要
**Describe the bug** For tables defined with version column and is_deleted: ENGINE = ReplacingMergeTree(version_col, is_deleted) metadata reflection fails with following: metadata.reflect(bind=engine, schema=db_name) *** sqlalchemy.exc.ConstraintColumnNotFoundError: Can't create TableCol on table 'myThirdReplacingMT ': no column named 'version_col, is_deleted' is present.` The issue lays in insufficient parsing logic...
