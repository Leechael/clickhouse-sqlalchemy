# Issue #400 Asynch driver incompatible with asynch 0.3.1+ and SQLAlchemy 2.0.44+

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/400
- Category: 我们可以跟进修复
- Priority: high
- Created: 2026-02-23T18:22:57Z
- Updated: 2026-02-24T00:08:19Z
- Author: kusaku
- Labels: none
- Comments: 0

## 判断
asynch 兼容汇总 issue；本地已有多项修复，但还需要对 asynch fork 版本做回归验证。

## 本地 fork 现状
本地 pyproject 使用 Leechael/asynch fork；AsyncAdapt_asynch_cursor 已有 _async_soft_close，commit/rollback 捕获 NotSupportedError。

## 建议动作
跑 asynch driver 相关测试并补参数格式/百分号回归用例，确认 fork 后兼容问题是否仍存在。

## Issue 摘要
**Describe the bug** The asynch driver in clickhouse-sqlalchemy has several compatibility gaps: 1. **asynch 0.3.1+** – Parameter substitution changed from `%` formatting to Python `.format()`, which expects `{name}` instead of `%(name)s`. Queries and data containing `%` can break. 2. **SQLAlchemy 2.0.44+** – Async cursor must implement `_async_soft_close()` for proper cleanup. 3. **ClickHouse semantics** – `commit` a...
