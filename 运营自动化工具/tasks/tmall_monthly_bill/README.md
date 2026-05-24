# 猫超月账单整理

统一入口：

```bash
python3 run.py 猫超账单整理 --dry-run --skip-auto-download
```

当前实现分两层：

- 下载阶段：统一委托给 `ops --json tmcs bill download` 与 `ops --json tmcs promotion-bill download`
- 业务整理阶段：继续使用本目录 `processor.py` 做 Excel 归档和月账单生成

正式下载链路：

- `python3 run.py 猫超账单整理`
- `运营自动化工具` 先检查本次 `--bill-dir`
- 若目录里已有 `HDB*.xlsx`、`对账单列表.xlsx`、推广账单源文件，则直接复用
- 缺失时再调用 `Ops-Cli`
- `Ops-Cli` 通过 SessionHub `9222` 专用浏览器执行真实下载
- 在交互终端中，如果账单或推广下载 scene 登录态失效，业务入口会自动转入 `--interactive-login`；`Ops-Cli` 拉起 `9222` 页面等待手动登录，登录后自动刷新目标页并重试一次
- `--dry-run` 和无 TTY 执行不会等待登录；失效时返回状态或 `AUTH_REQUIRED`

当前生成结果包含：

- 主账单 sheet
- `货款表格`
- `票扣表格`
- `账扣表格`
- `开票表`
- `成本表`
- `对账单列表`
- `万相台推广数据表格`
- `智多星推广数据表格`

输出规则：

- 最终生成的 `猫超{month}月账单数据表格.xlsx` 直接写到桌面
- 原始 `HDB*.xlsx`
- `对账单列表`
- 推广账单源文件

都会保留在原来的下载或传入位置，不再移动

并且会在 `开票表` 右侧空两列后生成一块利润汇总区域，汇总：

- 销售金额
- 实际成本
- 营销推广
- 票扣
- 账扣
- 最终利润

新增数据来源同样统一走 `Ops-Cli`：

- `对账单列表` 通过现有账单下载链路获取
- `万相台推广数据表格` 通过 `ops --json tmcs promotion-bill download --source wxt`
- `智多星推广数据表格` 通过 `ops --json tmcs promotion-bill download --source zdx`

智多星平台导出为完整资金流水，sheet 保留原始全部行；利润汇总只在本次 HDB 账期内筛选 `类型=从冻结中转出` 的记录，避免跨月金额叠加。

其中账单下载内部链路是：

- `statement_bill_list_for_supplier` 获取 HDB 列表
- `statement_bill_dynamic_list` 触发 `对账单列表` 导出
- `download_file_query` 作为下载中心兜底查询

统一源文件规则：

- 优先使用本次运行传入的下载目录 `--bill-dir` 里的现成源文件
- 只有下载目录里缺失对应文件时，才触发浏览器 / CLI 下载链路
- 真实下载默认走 `9222` SessionHub 浏览器，不依赖 Codex 直接接管主浏览器点页面

边界：

- 本项目负责账单整理业务规则
- `Ops-Cli` 负责猫超账单平台下载
- 旧 Copy as cURL fallback 参数已移除，不再从业务层透传 cURL 文件
