# Issue #365 Is there any plan to support clickhouse new feature generateSerialID?

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/365
- Category: 我们可以跟进修复
- Priority: low
- Created: 2025-03-04T01:01:00Z
- Updated: 2025-04-15T01:08:09Z
- Author: flyly0755
- Labels: none
- Comments: 1

## 判断
generateSerialID 是 ClickHouse 新函数/特性，可作为函数支持或文档示例。

## 本地 fork 现状
当前未见专门 generateSerialID helper。

## 建议动作
确认 SQLAlchemy func.generateSerialID 是否足够；必要时添加函数编译测试/文档。

## Issue 摘要
Now clickhouse support auto-increment id column(can start from int 1) in clickhouse25. https://clickhouse.com/blog/clickhouse-release-25-01 Which is very useful. So I wonder your guys is there any plan to support the corresponding feature in clickhouse-sqlalchemy(especially ORM side).
