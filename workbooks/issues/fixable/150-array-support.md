# Issue #150 Array support

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/150
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2021-10-19T20:18:56Z
- Updated: 2025-04-05T18:47:56Z
- Author: royxact
- Labels: feature request
- Comments: 3

## 判断
Array 支持，本地已有 Array 类型、DDL、插入测试。

## 本地 fork 现状
types.Array、typecompiler.visit_array 和多处 tests 覆盖。

## 建议动作
若 issue 指特定 Array 场景，需跟 #195/#328 细分；基础支持已存在。

## Issue 摘要
Hi and thanks for this cool package! Now for the issue: it seems when selecting an Array column, we get it back as a string. I saw in the code that arrays are converted to string. Can an array be represented as a python array, similar to how it's in postgres? Thanks! Roy
