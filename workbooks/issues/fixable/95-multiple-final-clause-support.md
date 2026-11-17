# Issue #95 Multiple FINAL clause support

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/95
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2020-05-25T19:56:36Z
- Updated: 2022-07-05T18:54:14Z
- Author: xzkostyan
- Labels: bug
- Comments: 1

## 判断
多表 JOIN/逗号 FROM 的 FINAL 支持缺失。

## 本地 fork 现状
docs 明确 FINAL 仅支持主 FROM；compiler 只追加一个 FINAL。

## 建议动作
设计 per-table final 标记或通过 settings final=1 文档化。

## Issue 摘要
**Describe the bug** It's not possible to control `FINAL` rendering with JOINs. ``` sql CREATE TABLE test_int2 (x Int32, sign Int8) ENGINE = CollapsingMergeTree(sign) ORDER BY tuple(); ``` Query examples: ```sql select x from test_int2 as a final join test_int2 as b final on a.x = b.x; ``` ```sql select * from test_int2 as a final, test_int2 as b final; ````
