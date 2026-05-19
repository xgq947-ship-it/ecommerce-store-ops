# Ops-Cli 架构设计

## 定位

`Ops-Cli` 是平台能力层，不是业务工作流层。

- 负责平台接入：JST、TMCS、浏览器自动化、CDP、SessionHub、请求模板、平台鉴权
- 负责统一接口：`ops ...`
- 负责统一输出：JSON、日志、上下文、截图、模板
- 不负责业务编排：Excel 汇总、买家秀、NAS 流程、自然语言分发

## 分层

```text
CLI
  -> integrations
  -> platforms/jst
  -> platforms/tmcs
  -> utils
  -> output/logger/runtime_context
```

## 目录职责

- `src/ops_cli/cli.py`
  - 唯一正式 CLI 入口
- `src/ops_cli/integrations/sessionhub.py`
  - 统一接 SessionHub scene 校验 / capture / ensure
- `src/ops_cli/platforms/jst/`
  - 聚水潭全部平台逻辑
- `src/ops_cli/platforms/tmcs/`
  - 猫超全部平台逻辑
- `src/ops_cli/output.py`
  - 统一 JSON 输出结构
- `src/ops_cli/logger.py`
  - 统一日志格式
- `src/ops_cli/runtime_context.py`
  - 统一上下文记录

## 边界

以下代码只能放在 `Ops-Cli`：

- 平台 URL
- Cookie / Token / LocalStorage
- Playwright / CDP / 浏览器页面操作
- Selector / 页面点击 / 上传下载
- requests / httpx 直接请求平台
- Scene 学习与请求重放

以下代码不能再放回 `运营自动化工具`：

- `requests.post("https://www.erp321.com/...")`
- `requests.post("https://wdksettlement.hemaos.com/...")`
- `browser_cookie3`
- `connect_over_cdp`
- `sessionhub` 内部 import

## 调用关系

```text
运营自动化工具/run.py
  -> tasks/*
  -> subprocess
  -> ops --json ...
  -> Ops-Cli
```

## 当前兼容点

- `SESSIONHUB_ROOT` 当前默认指向 `/Users/dasheng/Desktop/电商Brain/02-运营店铺/Ops-Cli/sessionhub`
- 这是会话资产目录兼容，不再意味着平台逻辑归业务项目
