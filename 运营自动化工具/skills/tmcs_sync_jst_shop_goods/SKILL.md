---
name: tmcs-sync-jst-shop-goods
description: Use when the user asks to synchronize one or more 猫超平台商品ID into 聚水潭店铺商品资料, including phrases such as 聚水潭商品信息同步猫超, 猫超商品信息同步聚水潭, 平台商品ID同步聚水潭, or 猫超商品同步聚水潭.
---

# 猫超商品信息同步聚水潭

## 标准入口

用户提供平台商品 ID 并要求同步时，直接执行真实导入：

```bash
cd /Users/dasheng/Desktop/电商Brain/02-运营店铺/运营自动化工具
python3 run.py 聚水潭商品信息同步猫超 \
  --item-ids 1052305450766 \
  --import-jst \
  --import-mode cover
```

典型触发语句：

```text
1052305450766 聚水潭商品信息同步猫超
```

## 批量输入

多个平台商品 ID 使用英文逗号分隔：

```bash
python3 run.py 聚水潭商品信息同步猫超 \
  --item-ids 1052305450766,1052305450767 \
  --import-jst \
  --import-mode cover
```

从 Excel 读取时使用 `--input-file`。支持列名：`平台商品ID`、`商品ID`、`item_id`、`itemId`、`platform_item_id`。

## 仅生成导入表

仅在用户明确要求预览、不导入时使用：

```bash
python3 run.py 聚水潭商品信息同步猫超 \
  --item-ids 1052305450766 \
  --no-import
```

## 边界

- 当前业务任务只做输入解析、Excel 生成、任务编排和结果汇总。
- 猫超数据查询统一调用 `Ops-Cli` 的 `tmcs stock query` 接口能力。
- 聚水潭导入统一调用 `Ops-Cli` 的 `jst shop-goods import` 能力。
- 不在本 skill 内写平台 URL、Cookie、Token、selector 或浏览器操作。

## 回报

真实执行后回报：

- 商品 ID 和猫超查询返回行数。
- 聚水潭导入成功数、失败数和目标店铺。
- 导入 Excel、失败 Excel（如有）、日志、截图及 `runtime/context` 路径。
