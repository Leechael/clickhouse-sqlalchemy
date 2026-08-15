# Issue #345 Add the "pyproject.toml" file backended with building/packaging/dependency manager.

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/345
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2024-10-30T16:11:03Z
- Updated: 2025-05-30T09:04:15Z
- Author: stankudrow
- Labels: none
- Comments: 0

## 判断
pyproject/现代构建配置请求，本 fork 已有 PDM pyproject。

## 本地 fork 现状
pyproject.toml 使用 pdm-backend，包含依赖、entry points、脚本。

## 建议动作
可标为本 fork 已完成；仅需确认是否发布包带上配置。

## Issue 摘要
Python packages move to the "pyproject.toml" file as a single and standard source of project metadata. Practically all modern project managers like uv, poetry, pdm, setuptools and so forth support [PEP-621](https://peps.python.org/pep-0621/) . It's (high) time for this project to adopt new trends.
