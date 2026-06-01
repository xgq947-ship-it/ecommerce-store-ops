# Ops-Cli 调用规范

## 调用入口

业务项目统一通过：

```bash
ops --json ...
```

或通过：

[`clients/ops_cli_client.py`](/Users/dasheng/Desktop/电商Brain/02-运营店铺/运营自动化工具/clients/ops_cli_client.py)

## 当前映射

- `update_jst_products` -> `ops --json jst product sync`
- `update_maochao_goods` -> `ops --json tmcs product sync`
- `tmcs_sync_jst_shop_goods` -> `ops --json tmcs stock query` + `ops --json jst shop-goods import`
- `tag_jst_brush_orders` -> `ops --json jst order label`
- `jst_brush_reimburse_workorder` -> `ops --json jst order reimburse`
- `jst_order_invoice_workorder` -> `ops --json jst order invoice`
- `tmall_monthly_bill/downloader.py` -> `ops --json tmcs bill download`
- `tmcs_xp_workorder_watch` -> `ops --json tmcs xp-workorder count`
- `jst_pickup_watch` -> `ops --json jst order pickup-watch --hours 48`

不走 `Ops-Cli` 平台请求、只读本地数据的能力：

- `tmcs_sku_roi` -> 读取 `主数据/猫超商品列表导出 (最新）.xlsx`、`主数据/聚水潭商品资料（最新）.xlsx`、`config/tmcs_sku_roi.json`

## 返回约定

业务层只读取：

- `success`
- `platform`
- `command`
- `data`

其中统一可用字段为 `data.artifacts`、`data.context_path` 与 `data.session_recovery`。失败时只读取 JSON 中的 `error_code`、`retryable` 和 `recovery_hint`，不得解析 stderr 的登录提示或浏览器文案。

## 错误处理

- `Ops-Cli` 返回非 0：任务直接失败
- `stdout` 非 JSON：任务直接失败
- 业务层不得自行 fallback 到直连平台
- 真实 `jst` / `tmcs` 平台调用前，`clients/ops_cli_client.py` 会按平台在当前业务进程内先执行一次 `ops --json --interactive-login <platform> auth ensure`；后台自动化和手动入口复用同一行为
- 认证预检失败时不执行后续业务请求；登录、页面启动和 scene 恢复仍由 `Ops-Cli` 使用 `9222` 处理
- `--dry-run` 与 `auth` 命令不触发前置预检；预检后的业务请求若再次返回 `AUTH_REQUIRED`，交互终端调用仍会追加 `--interactive-login` 重试一次，失败时保留 context
