# Issue #211 with uri clickhouse://  to insert data with  integer field, there isn't range check, can insert successfully with out of range integer value

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/211
- Category: 问答
- Priority: medium
- Created: 2022-11-03T03:56:25Z
- Updated: 2022-11-03T03:56:25Z
- Author: flyly0755
- Labels: none
- Comments: 0

## 判断
整数越界插入与 #270 重复，默认不做全面客户端校验。

## 本地 fork 现状
native 支持 types_check=True；其他 driver 需确认。

## 建议动作
合并到 #270 的处理建议。

## Issue 摘要
**Describe the bug** clickhouse-sqlalchemy support 2 kinds of uri uri = 'clickhouse+native://localhost/default' with native tcp port(9000) uri = 'clickhouse://localhost/default' with http port(8123) with http mode, for example, I have a uint32 field called u32fd, insert data 908,603,248(‭0011 0110 0010 1000 0010 1111 0111 0000‬) to u32fd, can insert successfully. But the real value in database is 12144, which is cut ...
