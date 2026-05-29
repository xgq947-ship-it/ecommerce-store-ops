# AGENTS.md

## 项目定位

这是 `/Users/dasheng/Desktop/电商Brain/02-运营店铺/运营自动化工具` 的长期本地电商运营自动化项目。默认环境是 macOS + Zsh，业务围绕天猫超市、聚水潭 ERP、公司 NAS、Excel/WPS 表格和本地文件流。

所有长期任务必须服务于“统一入口、可复用登录态、可追踪运行记录、可安全回放”的架构，不要把一次性脚本散落到项目外。

## 总体架构

稳定链路：

```text
主浏览器学习接口 -> Ops-Cli/sessionhub 沉淀 scene -> Ops-Cli 平台接口 -> 运营工具 tasks 编排业务流程 -> run.py 统一调度
```

当前核心层：

- `run.py`：唯一统一任务入口，只做任务解析、调度、Python 环境选择、日志和 `runtime/context` 记录。
- `core/task_registry.py`：任务注册和触发词来源，通过扫描 `tasks/` 下的 `task.yaml` 动态加载。
- `tasks/`：业务任务目录，负责具体流程、参数解析、dry-run、业务日志和输出。
- `clients/`：只保留业务侧到 `Ops-Cli` 的桥接。
- `Ops-Cli/sessionhub/`：统一登录态中心、9222 Chrome 会话入口、动态请求捕获入口，不放业务逻辑。
- `Ops-Cli/src/ops_cli/capabilities.py` 与 `execution.py`：统一能力注册（各平台通过 `platform.py` 的 `register()` 动态注册）、交互登录策略、JSON 输出和错误分类入口。
- `runtime/context/`：任务运行上下文记录，用于追踪输入、输出、产物、错误和下游任务。
- `runtime/retry/`：可重放失败项，不替代失败 Excel、业务日志或人工验收。
- `logs/`：任务执行日志。

## 双浏览器接口学习架构

Codex 插件只能绑定主浏览器；SessionHub 使用 9222 专用浏览器。两者职责必须分开。

- 主浏览器是日常 Chrome，绑定 Codex 插件，用于自动打开页面、点击查询/导出/详情/提交、触发后台接口、观察 Network 请求和提取接口结构；主浏览器只负责“接口学习”，不用于正式生产执行。
- 主浏览器请求只能生成 template，不允许直接作为正式 session 使用。
- template 只保留 `url pattern`、`method`、参数结构、`body schema`、header names、response structure、trigger steps。
- 禁止从主浏览器复用 `cookie`、`token`、`authorization`、`csrf`、`x-token` 和任何登录态 headers。
- 9222 Chrome 是 SessionHub 专用浏览器，使用独立 profile，负责真实生产 session、scene/session 管理和稳定 API 执行。
- 正式执行链路必须是 `template -> 9222 session -> scene -> Ops-Cli 平台命令 -> 运营工具 tasks -> run.py`。
- 新增 skill 或后台自动化时，优先自动学习接口，不再默认要求用户手工复制 cURL 或打开 F12。
- Codex 插件定位为页面动作层，不是长期生产层。
- SessionHub 定位为 scene/session 管理中心、动态接口学习中心和生产请求执行中心。

## SessionHub 规则

SessionHub 只做基础会话能力：

- 启动、关闭、检查 9222 专用 Chrome。
- 导出和检查猫超、聚水潭 Cookie。
- 捕获允许域名下的接口请求。
- 保存 platform session 和 scene session。
- 为业务脚本提供可复用 session/cookie/token/header。

SessionHub 不做：

- 不写业务 Excel。
- 不处理猫超账单、猫超商品、聚水潭同步、刷单、买家秀、公司 NAS 等具体业务。
- 不注册为业务任务。
- 不引入数据库、前端页面或常驻复杂服务。

动态 scene 配置放在 `Ops-Cli/sessionhub/config/sites/*.yaml`。scene 必须描述目标页面、URL 匹配片段、请求方法和 `auto_actions`，并支持 `wait_seconds`、`capture_retry_limit`、`sensitive_artifact_policy`。已有 scene 包括：

- `tmall_chaoshi/download_file_query`
- `tmall_chaoshi/statement_bill_dynamic_list`
- `tmall_chaoshi/maochao_item_search`
- `jst_erp/order_list`
- `jst_erp/product_export`

请求捕获域名只允许：

- `erp321.com`
- `jushuitan.com`
- `tmall.com`
- `taobao.com`

## run.py 边界

`run.py` 只负责调度，不写复杂业务逻辑。

允许：

- 解析任务名和自然语言触发词。
- 调用 `core.task_registry.resolve_task()`。
- 选择 Python 解释器。
- 调用任务脚本。
- 写外层日志和 `TaskContext`。

不允许：

- 写平台接口请求逻辑。
- 写 Excel 处理逻辑。
- 写复杂自然语言业务参数解析。
- 写浏览器登录、Cookie、Token 管理逻辑。

复杂参数解析应放回对应任务自己的 adapter。

## tasks 规则

新增长期业务必须放到 `tasks/`，并创建对应的 `task.yaml` 声明文件（自动注册，无需手动修改 `task_registry.py`）。

任务应遵守：

- 支持 `--dry-run`。
- 写操作默认保守，真实写入必须明确。
- 业务参数解析留在任务内部。
- 平台调用统一走 `clients/ops_cli_client.py`。
- 不直接导入 SessionHub 内部实现。
- 需要运行追踪时写 `TaskContext`。
- 有可重放失败项时写 `runtime/retry/`。
- 长期路径和业务数据源路径必须写入 `config/paths.yaml`，通过 `core.config_loader.get_path()` 读取；任务内不要新增硬编码绝对路径。项目相对路径（runtime_dir、logs_dir 等）已内置在 `DEFAULT_PATHS` 中，个人路径（桌面、下载、微信文件等）需在 `config/paths.yaml` 中配置，缺失时会提示参考 `config/paths.yaml.example`。

## clients 规则

`clients/` 是共享适配层，默认只保留业务侧到 `Ops-Cli` 的桥接。

- 默认入口：`clients/ops_cli_client.py`。
- tasks 不应重复拼装通用平台请求、登录态、Cookie 和 Token。
- tasks 只消费 `ops --json` 的单一 stdout JSON 文档；stderr 的登录/浏览器提示只用于诊断。

## runtime 和 retry 规则

`runtime/context/*.json` 用于记录任务运行，不作为长期业务主数据。

context 应尽量包含：

- 输入参数。
- 输出摘要。
- 产物路径。
- 错误摘要。
- 下游任务信息。

`runtime/retry/*.json` 只保存明确可重放的失败项。重放默认 dry-run，只有显式 `--execute` 才允许真实执行。retry queue 不能替代失败 Excel、任务日志或业务表。

## Excel 和文件规则

- 涉及 WPS/Excel 图片、`DISPIMG`、`xl/cellimages.xml`、截图资源时，必须优先保留原文件结构。
- 不要用普通整本 `openpyxl.save()` 覆盖已有图片结构的登记表，除非已确认不会破坏图片。
- 用户说“移动”就按 move 处理，不擅自 copy。
- 写入、覆盖、清空、移动文件前要确认业务流和输出落点。

## 猫超和聚水潭规则

- 猫超和聚水潭后台自动化优先走 `Ops-Cli` 内的 API/CDP/SessionHub 能力，不改成 Selenium。
- 登录态统一复用 `Ops-Cli/sessionhub` 的 9222 Chrome 和 scene。
- 交互终端执行时，session 失效由 `Ops-Cli` 自动拉起 `9222`、等待手动登录、捕获后重试一次。
- `--dry-run`、`auth check` 和无 TTY 调用不等待登录；失效时返回状态或 `AUTH_REQUIRED`，不要静默 fallback。
- 平台接口沉淀到 `docs/apis/` 和 scene 配置时，避免包含敏感 Cookie/Token 明文。

## 新增任务流程

新增业务能力的标准路径：

1. 用主浏览器学习页面和接口。
2. 在 `Ops-Cli/sessionhub` 中沉淀或更新 scene。
3. 在 `Ops-Cli` 中封装可复用平台命令。
4. 在 `tasks/` 实现业务编排。
5. 在任务目录创建 `task.yaml` 声明 name、aliases、fuzzy_keywords、required_modules、entrypoint（自动注册，无需手动修改 `task_registry.py`）。
6. 用 `run.py` 验证入口、dry-run、日志和 context。
7. 必要时同步 `README.md`、项目 `SKILL.md` 和全局 skill。

## 禁止事项

- 不把业务逻辑写进 `sessionhub/`。
- 不把复杂业务解析写进 `run.py`。
- 不让 tasks 直接管理浏览器启动、登录、Cookie、Token。
- 不绕过 `run.py` 新增长期入口。
- 不默认引入数据库、前端页面或常驻服务。
- 不把临时探索代码当长期任务提交。
- 不破坏已验证的 SessionHub 核心结构和现有任务命令。
- 不把敏感 Cookie、Token、Authorization 明文写入文档、日志或示例。
