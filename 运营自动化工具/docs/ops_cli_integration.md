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
- `tag_jst_brush_orders` -> `ops --json jst order label`
- `jst_brush_reimburse_workorder` -> `ops --json jst order reimburse`
- `tmall_monthly_bill/downloader.py` -> `ops --json tmcs bill download`

## 返回约定

业务层只读取：

- `success`
- `platform`
- `command`
- `data`

## 错误处理

- `Ops-Cli` 返回非 0：任务直接失败
- `stdout` 非 JSON：任务直接失败
- 业务层不得自行 fallback 到直连平台
