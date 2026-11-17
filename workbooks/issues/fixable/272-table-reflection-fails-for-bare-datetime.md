# Issue #272 Table reflection fails for bare DateTime

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/272
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2023-10-30T18:12:49Z
- Updated: 2023-10-30T18:12:49Z
- Author: hsheth2
- Labels: none
- Comments: 0

## 判断
bare DateTime 反射失败；本地已有 DateTime 与 DateTime64 反射测试。

## 本地 fork 现状
tests/test_reflection.py 覆盖 DateTime64；base ischema_names 有 DateTime。

## 建议动作
补 bare DateTime 专项测试或跑现有 reflection 测试确认。

## Issue 摘要
```sql CREATE MATERIALIZED VIEW db1.mv_with_target_table TO db1.mv_target_table ( `col_DateTime` DateTime, `col_Int64` Int64, `col_Float64` Float64, `col_Decimal64` Decimal(18, 5), `col_String` String ) AS SELECT col_DateTime, col_Int64, col_Float64, col_Decimal64, col_String FROM db1.test_data_types; ``` Seeing this error when using reflection to get columns: ``` DateTime.__init__() takes from 1 to 2 positional argu...
