# Issue #398 No way to omit parameters for Replicated* table engines constructor

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/398
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2025-12-09T04:03:02Z
- Updated: 2025-12-09T04:03:02Z
- Author: bgo-bc
- Labels: none
- Comments: 0

## 判断
Replicated* 引擎现在要求 table_path/replica_name，但 ClickHouse 新版本允许省略。

## 本地 fork 现状
ReplicatedEngineMixin 与各 Replicated* 构造函数仍要求两个位置参数。

## 建议动作
允许 table_path/replica_name 为 None 或省略，并让参数渲染支持空 ReplicatedMergeTree。

## Issue 摘要
**Describe the bug** Clickhouse allows omitting the parameters for Replicated* engines (https://clickhouse.com/docs/engines/table-engines/mergetree-family/replication) ``` For example, in the text below you would replace: ENGINE = ReplicatedMergeTree( '/clickhouse/tables/{shard}/table_name', '{replica}' ) with: ENGINE = ReplicatedMergeTree ``` But in clickhhouse-sqlalchemy, the table_path and replica_name are require...
