# 运营自动化工具架构说明

## 定位

这是业务编排层，不是平台层。

## 只允许做的事

- skill 触发
- 业务工作流编排
- Excel 生成 / 回写
- 路径管理
- 日志与上下文记录
- retry queue
- subprocess 调 `Ops-Cli`

## 禁止做的事

- 平台 API 请求
- Cookie / Token 管理
- Playwright / CDP / 浏览器控制
- Selector / 页面 URL
- SessionHub 内部导入

## 当前结构

```text
run.py
  -> core/task_registry.py
  -> tasks/*
  -> clients/ops_cli_client.py
  -> ops --json ...
  -> Ops-Cli capability runner
```

## 说明

`sessionhub/` 已迁移到 `Ops-Cli/sessionhub`；本项目不再保存平台会话资产。

业务侧只解析 `ops --json` stdout 中的 `success/data/error_code/context_path/session_recovery`。登录等待、浏览器启动和 scene 重试由 `Ops-Cli` 处理并写入 stderr，本项目不解析这些提示文本，也不自行恢复 session。
