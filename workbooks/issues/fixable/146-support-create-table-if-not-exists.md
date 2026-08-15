# Issue #146 Support CREATE TABLE IF NOT EXISTS

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/146
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2021-10-02T16:18:28Z
- Updated: 2022-07-05T18:25:09Z
- Author: robinovitch61
- Labels: feature request
- Comments: 0

## 判断
CREATE TABLE IF NOT EXISTS 支持是 DDL API 增强。

## 本地 fork 现状
SQLAlchemy create_all(checkfirst=True) 可避免，但原生 IF NOT EXISTS 编译未见。

## 建议动作
新增 CreateTable(if_not_exists=True) 或 dialect option 设计。

## Issue 摘要
As far as I can tell, there's currently no way to add `IF NOT EXISTS` to a compiled `CREATE TABLE` expression. Would be great to have the option to add `IF NOT EXISTS`.
