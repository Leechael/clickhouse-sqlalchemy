# Issue #115 Support for timezone=True for types.DateTime

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/115
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2020-12-04T11:45:19Z
- Updated: 2022-07-05T18:50:58Z
- Author: Ginkooo
- Labels: feature request
- Comments: 1

## 判断
types.DateTime(timezone=True) 请求；本地支持 timezone 字符串但不支持 bool True 语义。

## 本地 fork 现状
DateTime.__init__(timezone=None) 接受 timezone 参数，compiler 渲染字符串。

## 建议动作
确认 issue 是否要求 SQLAlchemy DateTime(timezone=True) 自动映射；可补兼容。

## Issue 摘要
Hello, I have an enchantment proposal to make DateTime type optionally timezone-aware, like in sqlalchemy or DjangoORM. I think it would help to reduce many time offsetting issues in client codebases. It could use timezone attribute of Clickhouse's DateTime field or some default setting, what do you think?
