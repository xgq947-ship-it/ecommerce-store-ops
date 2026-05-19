# 猫超月账单整理

统一入口：

```bash
python3 run.py 猫超账单整理 --dry-run --skip-auto-download
```

当前实现分两层：

- 下载阶段：统一委托给 `ops --json tmcs bill download`
- 业务整理阶段：继续使用本目录 `processor.py` 做 Excel 归档和月账单生成

边界：

- 本项目负责账单整理业务规则
- `Ops-Cli` 负责猫超账单平台下载
- 旧 Copy as cURL fallback 参数已移除，不再从业务层透传 cURL 文件
