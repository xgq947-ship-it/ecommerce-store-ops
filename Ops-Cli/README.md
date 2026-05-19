# Ops-Cli

`Ops-Cli` 是两个项目里的唯一平台能力层。

- 负责：猫超、聚水潭、浏览器自动化、双浏览器学习、9222 SessionHub、Cookie/Session/LocalStorage、页面动作、上传下载、平台 API、统一 JSON 输出。
- 不负责：Excel 业务编排、刷单业务规则、买家秀编排、NAS 业务流程、自然语言任务分发。这些都留在 `运营自动化工具`。

## 当前支持的平台

- `tmcs`
  - 天猫超市 / 猫超
  - 商品列表同步
  - 库存导出 / 库存调整 / 一盘货库存查询
  - 月账单下载
- `jst`
  - 聚水潭认证检查
  - 商品资料导出同步
  - 订单打标
  - 订单物流查询
  - 订单统计 / 利润统计
  - 店铺商品导入
  - 发票工单能力
- `browser`
  - 9222 端口检查
  - 主浏览器学习辅助

## 架构边界

- `Ops-Cli` 只做平台能力，不做业务编排。
- 所有平台 URL、Cookie、Token、Selector、Requests、Playwright、CDP 连接、Scene 复检，都统一沉到这里。
- `运营自动化工具` 只能通过 `subprocess` 调用 `ops ...`，不能自己直接请求平台。

详细说明见：

- [架构设计](docs/architecture.md)
- [平台能力说明](docs/platform_capabilities.md)
- [双浏览器学习方案](docs/double_browser_learning.md)
- [9222 调试说明](docs/browser_9222_debug.md)
- [CLI 调用规范](docs/ops_cli_contract.md)

## 安装

```bash
cd /Users/dasheng/Desktop/电商Brain/02-运营店铺/Ops-Cli
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

或：

```bash
cd /Users/dasheng/Desktop/电商Brain/02-运营店铺/Ops-Cli
source .venv/bin/activate
pip install -e .
```

## 命令风格

统一只保留这种命名：

```bash
ops tmcs stock query
ops tmcs product sync
ops tmcs bill download
ops jst product sync
ops jst browser learn
ops jst shop-goods import
ops browser check
```

不再把 `python xxx.py`、`run_import.py`、`tmp_script.py`、`browser_test.py` 当成平台层正式接口。

## 常用命令

```bash
ops --help
ops --json browser check --port 9222

ops --json tmcs auth check
ops --json tmcs product sync
ops --json tmcs product sync --dry-run
ops --json tmcs product sync --use-local-only
ops --json tmcs product sync --force-refresh
ops --json tmcs bill download --last-month
ops --json tmcs bill download --download-statement-list --last-month
ops --json tmcs inventory export
ops tmcs stock query --item-ids 1052534376394,234567 --warehouse-code mc_aokesi_suolong --output json

ops --json jst auth check
ops --json jst product sync
ops --json jst product sync --dry-run
ops --json jst product sync --use-local-only
ops --json jst product sync --keep-brands 奥克斯 苏泊尔
ops --json jst order label --input /path/to/latest_brush_orders.json
ops --json jst order label --input /path/to/latest_brush_orders.json --limit 10
ops --json jst order label --input /path/to/latest_brush_orders.json --execute
ops --json jst order reimburse --outer-order-id 3302371490526182153 --principal-total 965 --payout-total 140 --product-code SUZBHLYZHH1001 --workbook-file /path/to/register.xlsx
ops --json jst order reimburse --outer-order-id 3302371490526182153 --principal-total 965 --payout-total 140 --product-code SUZBHLYZHH1001 --workbook-file /path/to/register.xlsx --execute
ops --json jst browser learn --scene shop-goods-import
ops --json jst shop-goods import --file /path/to/jst_shop_goods_import.xlsx --shop-name "（猫超）启明工贸有限公司" --mode cover --output json
```

## 环境变量

复制 `.env.example` 为 `.env`。

```env
SESSIONHUB_ROOT=/Users/dasheng/Desktop/电商Brain/02-运营店铺/Ops-Cli/sessionhub
PRIMARY_CHROME_CDP_URL=
JST_ORDER_STATS_STORE=（猫超）福安市启明工贸有限公司（肖国清）
JST_PRODUCT_SOURCE_PATH=/Users/dasheng/Downloads/聚水潭商品资料（最新）.xlsx
JST_PRODUCT_KEEP_BRANDS=奥克斯,苏泊尔
TMCS_PRODUCT_IMPORT_PATH=/Users/dasheng/Downloads/猫超商品列表导出.xlsx
TMCS_PRODUCT_LATEST_PATH=/Users/dasheng/Downloads/猫超商品列表导出 (最新）.xlsx
TMCS_BILL_DOWNLOAD_DIR=/Users/dasheng/Downloads
```

说明：

- `SESSIONHUB_ROOT` 当前默认指向 `Ops-Cli/sessionhub`，会话资产与平台执行代码放在同一个项目边界内。
- `PRIMARY_CHROME_CDP_URL` 只给主浏览器探测用，不能填 `9222`。
- `9222` 固定给 SessionHub 专用浏览器。

## 双浏览器学习机制

- 主浏览器：正在使用的普通 Google Chrome Default profile。
- 主浏览器用途：通过 Codex Chrome 插件接管，在独立 CDP 端口例如 `9223` 上做真实页面探测和真实请求学习。
- `9222` 浏览器：只给 SessionHub 长期沉淀 scene、复检和稳定执行。
- 禁止把“只用 9222 的单浏览器 capture”叫做双浏览器学习。

## 9222 机制

- 作用：稳定执行、长期复用、会话校验、scene 沉淀。
- 不作用：主浏览器日常探测。
- 推荐命令：

```bash
ops --json browser check --port 9222
ops --json tmcs auth ensure
ops --json jst auth ensure
```

## 输出标准

所有正式 CLI 都优先支持 `--json`，返回统一结构：

```json
{
  "success": true,
  "platform": "tmcs",
  "command": "product sync",
  "data": {}
}
```

统一约定：

- JSON 时间戳：ISO 8601，本地时区
- 文件名时间戳：`YYYYMMDD-HHMMSS` 或 `YYYYMMDD_HHMMSS`
- 日志目录：`logs/`
- 平台模板与长期资产：`data/`
- 运行上下文：`runtime/context/`
- 截图：`screenshots/` 或任务自己的截图目录
- 业务导出：`output/` 或命令说明中声明的固定目录

## 目录

```text
Ops-Cli/
  src/ops_cli/
    cli.py
    config.py
    output.py
    logger.py
    integrations/
    platforms/
      jst/
      tmcs/
  data/
  logs/
  runtime/
  docs/
```

## 与自动化运营项目的关系

`运营自动化工具` 现在统一通过：

```bash
ops --json ...
```

来调用平台层。

例如：

- `更新聚水潭资料` -> `ops --json jst product sync`
- `更新猫超商品列表` -> `ops --json tmcs product sync`
- `刷单订单插黄旗` -> `ops --json jst order label`
- `刷单报销登记` -> `ops --json jst order reimburse`
- `猫超账单下载` -> `ops --json tmcs bill download`

## 当前状态

- 平台能力文档已经集中到 `Ops-Cli/docs/`
- 运营项目的 skill / README / 任务文档已经改成调用 `Ops-Cli`
- `sessionhub` 资产目录已迁移到 `Ops-Cli/sessionhub`
