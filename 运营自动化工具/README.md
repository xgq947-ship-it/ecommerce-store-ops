# 运营自动化工具

这个项目现在只负责业务编排。

- 负责：skill、工作流、Excel 加工、任务分发、日志汇总、上下文记录、失败重试、NAS/买家秀/刷单等业务规则。
- 不负责：平台 API、Cookie、Token、Playwright、SessionHub 内部调用、浏览器自动化、平台 URL、Selector。

平台能力统一下沉到：

[`/Users/dasheng/Desktop/电商Brain/02-运营店铺/Ops-Cli`](/Users/dasheng/Desktop/电商Brain/02-运营店铺/Ops-Cli)

## 当前原则

- `run.py` 仍是统一业务入口
- 保留原中文任务名和模糊触发
- 具体平台动作统一通过 `subprocess -> ops --json ...`
- 不再在业务任务里直接请求 JST / TMCS
- 真实 `jst` / `tmcs` 平台调用在每个业务进程首次请求前，公共客户端会先以 `--interactive-login ... auth ensure` 做一次认证预检；手动执行和后台自动化统一生效
- 同一进程内同一平台只预检一次；`--dry-run` 与 `auth` 命令不触发前置预检。预检后业务请求再次返回 `AUTH_REQUIRED` 时，交互终端仍会以 `--interactive-login` 重试一次

## 统一架构

```text
运营自动化工具
  -> run.py
  -> tasks/*
  -> clients/ops_cli_client.py
  -> subprocess
  -> Ops-Cli
```

## 当前任务

- `append_brush_orders`
- `tag_jst_brush_orders`
- `jst_brush_reimburse_workorder`
- `buyer_show`
- `company_nas_listing`
- `company_nas_index`
- `process_maochao_bills`
- `update_jst_products`
- `update_maochao_goods`
- `tmcs_sync_jst_shop_goods`
- `retry_queue`
- `jst_pickup_watch`

## 任务与 Ops-Cli 的对应关系

- `更新聚水潭资料` -> `ops --json jst product sync`
- `更新猫超商品列表` -> `ops --json tmcs product sync`
- `刷单订单插黄旗` -> `ops --json jst order label`
- `刷单报销登记` -> `ops --json jst order reimburse`
- `猫超账单下载阶段` -> `ops --json tmcs bill download`
- `猫超账单整理` -> `ops --json tmcs bill download` + `ops --json tmcs promotion-bill download`
- `tmcs_sync_jst_shop_goods` skill -> `ops --json tmcs stock query` + `ops --json jst shop-goods import`
- `聚水潭揽收监控` -> `ops --json jst order pickup-watch`

## 常用命令

```bash
python3 run.py --list
python3 run.py 更新聚水潭资料 --dry-run --use-local-only
python3 run.py 更新猫超商品列表 --dry-run --skip-auto-download
python3 run.py 聚水潭商品信息同步猫超 --item-ids 1052305450766 --import-jst --import-mode cover
python3 run.py 刷单订单插黄旗 --dry-run --limit 1
python3 run.py buyer_show --buyer-show-path "/绝对路径/买家秀" --model "AQA-12D-838" --dry-run
python3 run.py buyer_show --buyer-show-path "/绝对路径/买家秀" --model "AQA-12D-838" --reset-rotation
python3 run.py 查看失败任务
python3 run.py 更新公司网盘索引 --dry-run
python3 run.py 聚水潭揽收监控 --dry-run
python3 run.py 聚水潭揽收监控 --dry-run --notify
```

## 聚水潭订单揽收监控

业务入口会读取近 48 小时已付款订单的 Ops-Cli JSON，统一用 `effective_pay_time` 计算风险：猫超订单优先用 `maochao_real_pay_time`，否则将聚水潭付款时间减去配置的 30 分钟；其他订单使用聚水潭付款时间。阈值、揽收关键词、仓库 17:30 停发规则都在配置文件中维护，不写入业务代码。

配置文件：

```text
config/pickup_watch.json
```

报告目录和任务日志：

```text
output/pickup_watch/聚水潭揽收监控_YYYYMMDD_HHMMSS.xlsx
output/pickup_watch/聚水潭揽收监控_YYYYMMDD_HHMMSS.csv
logs/jst_pickup_watch_YYYYMMDD_HHMMSS.log
runtime/context/
```

手动执行：

```bash
python3 run.py 聚水潭揽收监控 --dry-run
python3 run.py 聚水潭揽收监控 --hours 48 --debug
python3 run.py 聚水潭揽收监控 --notify
```

`--dry-run` 不请求真实聚水潭、不真实发送微信，仍会生成报告和日志，并在结果 JSON 的 `notification.preview` 输出模拟微信内容。

### Hermes 微信配置

本任务沿用本机已有 Hermes Weixin `send_message_tool` 适配器，发送到 Hermes 已配置的微信会话，不使用企业微信 webhook。正式推送需先启用：

```bash
export HERMES_WECHAT_ENABLED=true
export HERMES_AGENT_ROOT="$HOME/.hermes/hermes-agent"   # 非默认安装位置时设置
export HERMES_ENV_PATH="$HOME/.hermes/.env"             # 非默认环境文件时设置
export HERMES_PYTHON_BIN="$HOME/.hermes/hermes-agent/venv/bin/python3"  # 非默认 Hermes Python 时设置
python3 run.py 聚水潭揽收监控 --notify
```

`HERMES_WECHAT_BASE_URL`、`HERMES_WECHAT_TOKEN`、`HERMES_WECHAT_RECEIVER` 预留给后续 HTTP 网关适配器；当前已验证的本机 Weixin adapter 使用 Hermes 自身环境和默认会话，不依赖企业微信 URL/token。发送时复用现有 Hermes 上下文恢复与重试能力，因此恢复发送超时下限为 45 秒。发送失败只记录到任务日志，不中断报表生成。

### 双击运行

```bash
chmod +x 聚水潭揽收监控.command
```

双击 `聚水潭揽收监控.command` 会在当前项目目录运行 `python3 run.py 聚水潭揽收监控 --notify`，执行完成后保留终端窗口。

### launchd 自动运行

每天固定在 `10:00`、`14:30`、`17:30`、`18:00` 执行，不按半小时轮询。

```bash
chmod +x install_pickup_watch_launchd.sh uninstall_pickup_watch_launchd.sh
./install_pickup_watch_launchd.sh
launchctl list | grep jst-pickup-watch
launchctl kickstart -k gui/$(id -u)/com.xgq947.jst-pickup-watch
tail -f logs/jst_pickup_watch.out.log
tail -f logs/jst_pickup_watch.err.log
```

卸载：

```bash
./uninstall_pickup_watch_launchd.sh
```

安装脚本会把 `launchd/com.xgq947.jst-pickup-watch.plist` 中的 `__PROJECT_DIR__` 替换成当前目录后复制到 `~/Library/LaunchAgents/`。

### crontab 备选

将 `/你的项目路径/运营自动化工具` 替换为本机实际目录：

```cron
0 10 * * * cd /你的项目路径/运营自动化工具 && /usr/bin/python3 run.py 聚水潭揽收监控 --notify
30 14 * * * cd /你的项目路径/运营自动化工具 && /usr/bin/python3 run.py 聚水潭揽收监控 --notify
30 17 * * * cd /你的项目路径/运营自动化工具 && /usr/bin/python3 run.py 聚水潭揽收监控 --notify
0 18 * * * cd /你的项目路径/运营自动化工具 && /usr/bin/python3 run.py 聚水潭揽收监控 --notify
```

真实聚水潭执行通过 `Ops-Cli` 复用现有 `jst order logistics` 查询链路：有快递单号时读取轨迹识别揽收节点，没有快递单号时直接进入未揽收风险判断，并按 `JST_ORDER_STATS_STORE` 筛选店铺。若聚水潭要求“查询轨迹”短信授权，先在聚水潭页面完成授权后重新执行；任务不会把授权失败误判为未揽收。当前待增强字段仅为猫超真实付款时间 `maochao_real_pay_time`。

## 买家秀说明

- `buyer_show` 默认按 `买家秀路径 + 型号 + batch` 维护分组轮询状态，状态文件在 `runtime/buyer_show_rotation_state.json`
- 如果素材目录存在分组文件夹，默认只按分组轮询，不再退回到全目录硬切图
- 每个订单文件夹默认最多取 5 张图，但分组只要大于 3 张即可执行；1-3 张仍视为图片不足
- 同型号命中多个日期时，会按日期拆分批次并分别生成 zip
- 只有当素材目录完全没有分组文件夹时，才允许退回散图模式
- `--dry-run` 会输出日期批次、将使用的分组、轮询游标前后位置，以及是否因为分组/图片不足而不能执行
- `--groups` 会跳过轮询状态，严格按显式分组执行

## Skill 约束

- skill 只能调业务入口或 `Ops-Cli`
- skill 不能写死 URL / Cookie / Selector / Token
- skill 不能直接 import `sessionhub/*`
- skill 需要同步 README、`SKILL.md`、`skill.yaml`

详见：

- [架构说明](docs/architecture.md)
- [项目边界说明](docs/project_boundary.md)
- [Skill 开发规范](docs/skill_development_spec.md)
- [Ops-Cli 调用规范](docs/ops_cli_integration.md)
- [迁移报告](docs/migration_report.md)

## 目录

```text
运营自动化工具/
  clients/
    ops_cli_client.py
  config/
    paths.yaml
  core/
  tasks/
  skills/
  logs/
  runtime/
  docs/
  run.py
```

## 目录边界

- `sessionhub/` 已迁移到 `Ops-Cli/sessionhub`
- 本项目不再保存 SessionHub 代码或会话资产
- 旧平台实现文档已经迁移到 `Ops-Cli/docs/`
