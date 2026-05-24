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
- `retry_queue`

## 任务与 Ops-Cli 的对应关系

- `更新聚水潭资料` -> `ops --json jst product sync`
- `更新猫超商品列表` -> `ops --json tmcs product sync`
- `刷单订单插黄旗` -> `ops --json jst order label`
- `刷单报销登记` -> `ops --json jst order reimburse`
- `猫超账单下载阶段` -> `ops --json tmcs bill download`
- `猫超账单整理` -> `ops --json tmcs bill download` + `ops --json tmcs promotion-bill download`
- `tmcs_sync_jst_shop_goods` skill -> `ops --json tmcs stock query` + `ops --json jst shop-goods import`

## 常用命令

```bash
python3 run.py --list
python3 run.py 更新聚水潭资料 --dry-run --use-local-only
python3 run.py 更新猫超商品列表 --dry-run --skip-auto-download
python3 run.py 刷单订单插黄旗 --dry-run --limit 1
python3 run.py buyer_show --buyer-show-path "/绝对路径/买家秀" --model "AQA-12D-838" --dry-run
python3 run.py buyer_show --buyer-show-path "/绝对路径/买家秀" --model "AQA-12D-838" --reset-rotation
python3 run.py 查看失败任务
python3 run.py 更新公司网盘索引 --dry-run
```

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
