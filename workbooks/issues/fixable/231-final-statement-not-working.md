# Issue #231 FINAL statement not working

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/231
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2023-02-07T20:10:09Z
- Updated: 2025-07-07T12:48:07Z
- Author: tvorogme
- Labels: none
- Comments: 5

## 判断
FINAL statement 不工作，和 #341/#198/#95 相关。

## 本地 fork 现状
当前 final() 只在主 FROM 后统一渲染，docs 说明 join 多表不全支持。

## 建议动作
根据 issue 形态补测试；多表 FINAL 可能需新 API。

## Issue 摘要
**Describe the bug** I'm using `.final()` but there are no changes in query. Code: ``` query = AccountActualStatesGQ.get_query(info) # SQLAlchemy query query = apply_requested_fields(info, query, AccountActualStates) qs = query.filter_by(**kwargs) qs = qs.final() <-- ``` Then I'm compiling query: ``` logger.warning(f'Query to clickhouse: {qs.statement.compile(compile_kwargs={"literal_binds": True})}') ``` And got `SE...
