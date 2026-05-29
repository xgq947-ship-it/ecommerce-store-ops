# 电商运营项目

这个仓库用于管理店铺运营相关的本地自动化能力，当前主要包含两部分：

- `Ops-Cli`
- `运营自动化工具`

它们的分工是固定的：

- `Ops-Cli` 负责平台能力
  这里处理猫超、聚水潭、浏览器自动化、SessionHub、`9222` 专用浏览器、平台接口调用、文件下载和统一 JSON 输出。
- `运营自动化工具` 负责业务编排
  这里承接日常运营任务入口、Excel 处理、业务规则、归档和给同事使用的稳定命令。

## 当前目录结构

```text
02-运营店铺/
├── Ops-Cli/
├── 运营自动化工具/
├── 买家秀图片生成提示词.md
├── 天猫运营提示词.md
└── 运营店铺索引.md
```

## 典型用法

平台层常用命令：

```bash
cd Ops-Cli
./.venv/bin/ops --json browser check --port 9222
./.venv/bin/ops --json tmcs bill download --last-month
./.venv/bin/ops --json tmcs bill download --download-statement-list --last-month
./.venv/bin/ops --json tmcs promotion-bill download --last-month
./.venv/bin/ops --json jst product sync
```

业务层常用命令：

```bash
cd 运营自动化工具
python3 run.py --list
python3 run.py 猫超账单整理
python3 run.py 更新猫超商品列表 --dry-run
python3 run.py 更新聚水潭资料 --dry-run
```

业务层还新增了 step 化的 workflow 入口（旧命令完全不受影响）：

```bash
cd 运营自动化工具
python3 run.py workflow demo --dry-run
python3 run.py workflow tmall_monthly_bill --dry-run
```

workflow 是既有任务的包装层：复用 `tasks/` 的成熟业务实现，把流程拆成可追踪的步骤，逐步落运行记录到 `runtime/runs/`。详见 [运营自动化工具/docs/workflow_runtime.md](运营自动化工具/docs/workflow_runtime.md)。

## 猫超月账单链路

当前猫超月账单整理已经走通正式链路：

1. `运营自动化工具/run.py 猫超账单整理`
2. 优先检查下载目录里是否已有源文件
3. 缺失时调用 `Ops-Cli`
4. `Ops-Cli` 通过 SessionHub `9222` 专用浏览器完成真实下载
5. 业务层生成最终月账单 Excel

相关源文件包括：

- `HDB*.xlsx`
- `对账单列表.xlsx`
- `万象台推广账单`
- `智多星推广账单`

最终产物是 `猫超{month}月账单数据表格.xlsx`。

智多星源表按平台原始全量流水保留；最终利润汇总按本次账期过滤智多星支出，避免跨月数据叠加。

## 约束

- 平台操作统一沉到 `Ops-Cli`
- 业务项目不直接复制 curl、重写登录、自己请求平台接口
- 新增接口学习默认采用双浏览器方法
  主浏览器负责探测真实页面
  `9222` 只负责 SessionHub 长期执行和复用

## 更多说明

- `Ops-Cli` 详细说明见 [Ops-Cli/README.md](Ops-Cli/README.md)
- `运营自动化工具` 详细说明见 [运营自动化工具/README.md](运营自动化工具/README.md)
