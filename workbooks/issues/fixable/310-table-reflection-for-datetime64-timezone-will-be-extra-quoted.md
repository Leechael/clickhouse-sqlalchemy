# Issue #310 Table reflection for DateTime64 timezone will be extra quoted

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/310
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-05-09T08:48:37Z
- Updated: 2024-05-09T08:48:37Z
- Author: littlebtc
- Labels: none
- Comments: 0

## 判断
DateTime64 timezone 反射额外加引号。

## 本地 fork 现状
typecompiler 渲染 timezone 会加单引号；反射解析需确认是否保留多余引号。

## 建议动作
补 DateTime64 timezone 反射测试并修 parse_arguments。

## Issue 摘要
**Describe the bug** Table reflection for DateTime64 timezone will be extra quoted **To Reproduce** If you have a table like ```python class TestTable(Base): time = Column(types.DateTime64(3, "UTC"), primary_key=True) __tablename__ = "test_table" __table_args__ = (engines.MergeTree(order_by=("time",)),) ``` The first migration and table creation will work as expected. But running `alembic revision --autogenerate` aft...
