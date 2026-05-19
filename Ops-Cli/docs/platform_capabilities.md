# 平台能力说明

## JST

当前命令：

- `ops --json jst auth check`
- `ops --json jst auth ensure`
- `ops --json jst auth capture`
- `ops --json jst product sync`
- `ops --json jst product learn`
- `ops --json jst order label`
- `ops --json jst order reimburse`
- `ops --json jst order logistics`
- `ops --json jst order logistics learn`
- `ops --json jst order stats`
- `ops --json jst order stats learn`
- `ops --json jst profit yesterday`
- `ops --json jst profit month`
- `ops --json jst profit learn`
- `ops --json jst browser learn --scene shop-goods-import`
- `ops --json jst shop-goods import --file ...`
- `ops --json jst order invoice`
- `ops --json jst order invoice learn`

已覆盖能力：

- 商品资料后台导出
- 刷单订单打标
- 刷单报销工单创建
- 店铺商品导入
- 订单物流查询
- 统计 / 利润查询
- 工单模板沉淀

## TMCS

当前命令：

- `ops --json tmcs auth check`
- `ops --json tmcs auth ensure`
- `ops --json tmcs auth capture`
- `ops --json tmcs product list`
- `ops --json tmcs product learn`
- `ops --json tmcs product sync`
- `ops --json tmcs inventory learn`
- `ops --json tmcs inventory export`
- `ops --json tmcs inventory adjust-learn`
- `ops --json tmcs inventory adjust`
- `ops tmcs stock query --item-ids ... --warehouse-code ... --output json`
- `ops --json tmcs bill learn`
- `ops --json tmcs bill download`
- `ops --json tmcs listing create`

已覆盖能力：

- 商品列表真实导出与长期主表同步
- 一盘货库存查询
- 库存导出 / 调整
- 月账单下载

## 浏览器能力

- `ops --json browser check --port 9222`
- `ops --json jst browser learn --scene ...`

## 输出标准

统一响应：

```json
{
  "success": true,
  "platform": "jst",
  "command": "product sync",
  "data": {}
}
```

常见 `data` 字段：

- `runtime_context`
- `latest_file`
- `import_file`
- `failed_file`
- `sync_summary`
- `template_path`
- `scene`

## 日志与资产

- 日志：`logs/app.log`
- 模板：`data/`
- 上下文：`runtime/context/`
- 截图：任务对应的 `screenshots/`
