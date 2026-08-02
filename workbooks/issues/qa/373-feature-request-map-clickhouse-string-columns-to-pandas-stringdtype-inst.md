# Issue #373 Feature request: map ClickHouse String columns to pandas StringDtype instead of object

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/373
- Category: 问答
- Priority: low
- Created: 2025-05-02T12:06:41Z
- Updated: 2025-05-02T12:07:27Z
- Author: bryzgaloff
- Labels: none
- Comments: 0

## 判断
pandas dtype 映射属于 pandas/结果消费层需求，不是当前 SQLAlchemy dialect 的直接职责。

## 本地 fork 现状
仓库没有 pandas 集成层。

## 建议动作
回复建议在 pandas read_sql 后 astype("string")，或另开专门 pandas adapter 设计。

## Issue 摘要
# Current behaviour (legacy) When using clickhouse-sqlalchemy together with pandas (for example, via `pandas.read_sql`), all ClickHouse `String` columns are currently mapped to pandas columns with the `object` dtype. This is the legacy pandas behaviour. **Since pandas 1.0 there is a dedicated `StringDtype` (`dtype="string"`)**, which provides much better integration with pandas' string methods, missing value handling...
