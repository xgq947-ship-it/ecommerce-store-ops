# tmcs_sync_jst_shop_goods

把猫超一盘货库存中的商品编码关系，生成聚水潭「导入店铺商品资料」Excel，并调用 Ops-Cli 完成聚水潭页面导入。

## 架构边界

- 自动化运营项目只做业务编排：读取输入、生成 Excel、调用 Ops-Cli、汇总结果。
- 猫超平台查询在 Ops-Cli：`ops --json tmcs stock query ...`
- 聚水潭双浏览器学习和页面导入在 Ops-Cli：`ops --json jst browser learn ...`、`ops --json jst shop-goods import ...`
- 正式页面导入若遇登录失效，交互终端由 `Ops-Cli` 接管 `9222` 恢复；无 TTY 返回结构化失败，不在 skill 内处理登录
- 本 skill 不直接处理 cookie、storage、selector、URL、headers，也不写猫超/聚水潭底层自动化代码。

## 学习聚水潭导入流程

```bash
cd /Users/dasheng/Desktop/电商Brain/02-运营店铺/运营自动化工具
python skills/tmcs_sync_jst_shop_goods/main.py learn
```

该命令会调用：

```bash
ops --json jst browser learn --scene shop-goods-import
```

## 只生成 Excel

```bash
python skills/tmcs_sync_jst_shop_goods/main.py run \
  --item-ids 123456,234567 \
  --no-import
```

## 从 Excel 读取商品ID

兼容字段：`平台商品ID`、`商品ID`、`item_id`、`itemId`、`platform_item_id`。

```bash
python skills/tmcs_sync_jst_shop_goods/main.py run \
  --input-file ./商品ID列表.xlsx \
  --no-import
```

## 生成并导入聚水潭

```bash
python skills/tmcs_sync_jst_shop_goods/main.py run \
  --item-ids 123456,234567 \
  --import-jst \
  --import-mode cover
```

内部调用：

```bash
ops --json tmcs stock query --item-ids 123456,234567 --warehouse-code mc_aokesi_suolong --output json
ops --json jst shop-goods import --file /path/to/jst_shop_goods_import.xlsx --shop-name "（猫超）启明工贸有限公司" --mode cover --output json
```

## 输出

- 导入表：`skills/tmcs_sync_jst_shop_goods/output/jst_shop_goods_import_YYYYMMDD_HHMMSS.xlsx`
- 失败表：`skills/tmcs_sync_jst_shop_goods/output/failed_items_YYYYMMDD_HHMMSS.xlsx`
- 日志：`skills/tmcs_sync_jst_shop_goods/logs/tmcs_sync_jst_shop_goods_YYYYMMDD_HHMMSS.log`

## 数据映射

| 聚水潭字段 | 来源 |
|---|---|
| 线上款式编码 | platform_item_id |
| 线上商品编码 | 条形码（barCode，经 Ops-Cli 标准化为 merchant_goods_code） |
| 线上国标码 | 空 |
| 平台店铺款式编码 | platform_item_id |
| 平台店铺商品编码 | supplier_goods_id |
| 原始商品编码 | 条形码（barCode，经 Ops-Cli 标准化为 merchant_goods_code） |
| 线上商品名称 | 空 |
| 线上颜色规格 | 空 |
| 商品标识 | Retail |
