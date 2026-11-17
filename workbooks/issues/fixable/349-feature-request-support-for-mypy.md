# Issue #349 Feature Request: Support for MyPy

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/349
- Category: 我们可以跟进修复
- Priority: low
- Created: 2024-11-08T10:31:27Z
- Updated: 2024-11-08T10:31:27Z
- Author: IAL32
- Labels: none
- Comments: 0

## 判断
MyPy 支持是可做的类型质量工作。

## 本地 fork 现状
未见 py.typed/mypy 配置。

## 建议动作
添加 py.typed、基础 typing 策略和有限 mypy 配置。

## Issue 摘要
**Describe the bug** Support for `mypy` **To Reproduce** Just import anything from another project that uses mypy. Currently, we need to add `# type: ignore[import-untyped]` to every import line. **Expected behavior** No mypy ignores. **Versions** - `clickhouse-sqlalchemy==0.2.7` - Python version: 3.12.4 I am willing to create a PR and add support for that.
