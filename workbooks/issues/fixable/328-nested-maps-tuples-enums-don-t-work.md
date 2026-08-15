# Issue #328 Nested maps, tuples, enums don't work

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/328
- Category: 我们可以跟进修复
- Priority: high
- Created: 2024-07-23T09:33:11Z
- Updated: 2024-07-29T13:41:30Z
- Author: FraterCRC
- Labels: none
- Comments: 2

## 判断
Nested Map/Tuple/Enum 复杂类型不工作，涉及类型编译/反射/插入。

## 本地 fork 现状
已有 Map/Tuple/Nested 类型，但复杂嵌套反射和数据路径需要更多测试。

## 建议动作
新增嵌套类型 round-trip/DDL/reflection 测试，逐层修。

## Issue 摘要
**Describe the bug** When you nest Tuple(Tuple) or Map(Enum) you get error **To Reproduce** CREATE TABLE color_map ( id UInt32, colors Map(Enum('hello' = 1, 'world' = 2), String) ) ENGINE = Memory; And try to compile type. **Expected behavior** Should be Map(Enum, String), we get error. **Versions** 0.2, but code still wrong in new versions python 3.10
