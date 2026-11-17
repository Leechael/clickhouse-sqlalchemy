# Issue #270 Insert int data which is out of datatype limit can be inserted successfully, without data check

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/270
- Category: 问答
- Priority: medium
- Created: 2023-10-28T06:51:59Z
- Updated: 2023-10-30T01:46:28Z
- Author: flyly0755
- Labels: none
- Comments: 0

## 判断
整数越界是否做客户端校验取决于 driver types_check。

## 本地 fork 现状
native tests 有 types_check=True 溢出测试；默认可能由 ClickHouse/driver 决定。

## 建议动作
回复建议 execution_options(types_check=True)；如 asynch/http 无等价能力再另开增强。

## Issue 摘要
**Describe the bug** ```python from sqlalchemy import Column, create_engine from clickhouse_sqlalchemy import engines, types from clickhouse_sqlalchemy.ext.declarative import declarative_base from sqlalchemy.orm import sessionmaker from sqlalchemy import insert as sainsert ChBase = declarative_base() class Uint16Table(ChBase): id = Column(types.UInt16, primary_key=True) intvalue = Column(types.UInt16) __tablename__ =...
