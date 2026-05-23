# 猫超商品列表更新

统一入口：

```bash
python3 run.py 更新猫超商品列表 --dry-run --skip-auto-download
```

当前实现：

- 业务入口仍在本项目
- 平台执行统一委托给 `ops --json tmcs product sync`
- 本任务不再自己调用 SessionHub、导出接口、URL 或 requests
- 交互终端登录恢复、无 TTY 快速失败与 `session_recovery` 输出统一由 `Ops-Cli` 处理

边界：

- 这里负责业务任务名兼容
- `Ops-Cli` 负责猫超商品导出、条码修复、主表同步
