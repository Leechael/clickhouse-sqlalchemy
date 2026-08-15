# Issue #98 prewhere support?

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/98
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2020-06-30T19:37:52Z
- Updated: 2022-07-05T18:53:46Z
- Author: akukareka-tm
- Labels: feature request
- Comments: 2

## 判断
PREWHERE 支持缺失。

## 本地 fork 现状
select/query 当前只有 where/final/sample/limit_by，没有 prewhere。

## 建议动作
添加 core .prewhere() 和 ORM .prefilter() API，按维护者建议命名。

## Issue 摘要
Hello, any plans for supporting Clickhouse prewhere clause?
