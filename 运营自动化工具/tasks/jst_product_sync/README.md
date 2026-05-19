# 聚水潭商品资料同步

统一入口：

```bash
python3 run.py 更新聚水潭资料 --dry-run --use-local-only
```

当前实现：

- 业务入口仍在本项目
- 平台执行统一委托给 `ops --json jst product sync`
- 本任务不再自己读取 SessionHub、URL、Cookie、Header

边界：

- 这里负责业务入口兼容
- `Ops-Cli` 负责聚水潭平台导出与同步
