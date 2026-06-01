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
- `ops --json jst order logistics --outer-order-id <订单号>`
- `ops --json jst order logistics --outer-order-id <订单号1> --outer-order-id <订单号2>`
- `ops --json jst order logistics --input <JSON/TXT/CSV路径> --limit <数量>`
- `ops --json jst order logistics learn`
- `ops --json jst order pickup-watch --hours 48 --dry-run`
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
- 订单物流单笔与批量查询，支持多次传参或 JSON/TXT/CSV 输入文件
- 订单揽收监控统一 JSON 契约与离线样本；真实执行复用订单列表分页与 `order logistics` 轨迹查询能力
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
- `ops --json tmcs stock query --item-ids ... --warehouse-code ... --output json`
- `ops --json tmcs bill learn`
- `ops --json tmcs bill download`
- `ops --json tmcs promotion-bill learn --source all`
- `ops --json tmcs promotion-bill download --last-month`
- `ops --json tmcs listing create`
- `ops --json tmcs xp-workorder count`
- `ops --json tmcs xp-workorder learn`

已覆盖能力：

- 商品列表真实导出与长期主表同步
- 一盘货库存查询
- 库存导出 / 调整
- 月账单下载：`HDB` 明细、`对账单列表`
- 推广账单下载：智多星、万象台；智多星保留平台完整资金流水 `.xlsx` 原表，万象台按页面真实返回保留 `.csv`
- XP 工单数量读取：直接从猫超首页可见文本提取 `XP工单处理 紧急(n)`，不再依赖接口计数返回

当前 TMCS 账单链路依赖的 scene：

- `statement_bill_list_for_supplier`
- `statement_bill_dynamic_list`
- `download_file_query`

其中：

- `statement_bill_list_for_supplier` 负责 HDB 列表查询
- `statement_bill_dynamic_list` 负责触发 `对账单列表` 导出任务
- `download_file_query` 负责查询下载中心文件

XP 工单监控当前口径：

- `tmcs xp-workorder count` 真实执行时会打开猫超首页 `https://web.txcs.tmall.com/`
- 从首页正文提取 `XP工单处理 紧急(n)`，输出 `count`
- `source` 字段为 `dom`
- `learn` 入口仅保留兼容说明，不再真正沉淀 scene
- `--dry-run` 返回 `simulated=true`

## 浏览器能力

- `ops --json browser check --port 9222`
- `ops --json jst browser learn --scene ...`

所有依赖 SessionHub 的正式交互 CLI 统一通过 capability runner 处理恢复链路：

- 自动拉起 `9222` 专用浏览器
- 等待手动登录
- 登录后按 scene 配置自动刷新页面或点击固定按钮
- 捕获到新 scene 后只重试原命令一次
- `--dry-run`、`auth check` 及无 TTY 调用不会自动恢复，可分别检查状态或返回 `AUTH_REQUIRED`
- 可用 `--interactive-login` / `--no-interactive-login` 显式覆盖终端判断

## 输出标准

统一响应：

```json
{
  "success": true,
  "platform": "jst",
  "command": "product sync",
  "data": {
    "capability_id": "jst.product.sync",
    "artifacts": [],
    "context_path": "runtime/context/...",
    "session_recovery": {
      "required": false,
      "interactive": false,
      "scenes_refreshed": [],
      "retry_count": 0
    }
  }
}
```

常见 `data` 字段：

- `context_path`
- `capability_id`
- `artifacts`
- `session_recovery`
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
