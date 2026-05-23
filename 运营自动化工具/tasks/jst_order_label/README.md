# 聚水潭刷单订单打标

统一入口：

```bash
python3 run.py 刷单订单插黄旗 --dry-run --limit 1
python3 run.py 刷单订单插黄旗 --dry-run --order-id 3302371490526182153
```

当前实现：

- 业务入口仍在本项目
- 平台执行统一委托给 `ops --json jst order label`
- 本任务不再自己处理 JST 请求、Cookie、SessionHub scene
- 交互终端登录恢复、无 TTY 快速失败与 `session_recovery` 输出统一由 `Ops-Cli` 处理

边界：

- 这里负责读取业务输入 `runtime/latest_brush_orders.json`
- 也支持通过 `--order-id` 临时传入单个或多个订单号做 dry-run / 重试
- `Ops-Cli` 负责真实订单查询、备注、标签写入
