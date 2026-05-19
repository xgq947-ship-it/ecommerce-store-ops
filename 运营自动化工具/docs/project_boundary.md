# 项目边界说明

## 统一结论

- `Ops-Cli`：所有平台操作
- `运营自动化工具`：所有业务编排

## Ops-Cli 负责

- 猫超
- 聚水潭
- 天猫超市
- 浏览器自动化
- 双浏览器学习
- Playwright
- Cookie / Session / LocalStorage
- 页面操作
- 上传下载
- API 请求
- 平台适配

## 运营自动化工具负责

- skill
- 工作流
- 数据加工
- Excel 生成
- 任务调度
- 日志汇总
- subprocess 调用 Ops-Cli
- 业务规则

## 运营自动化工具禁止项

- 平台 API
- 浏览器自动化
- Cookie / Token
- Playwright
- 直接 requests 调平台
- 页面 selector
- 平台 URL

## SessionHub 资产

- `sessionhub/` 目录已迁移到 `Ops-Cli/sessionhub`
- 本项目不再保存 SessionHub 代码或会话资产
- 平台消费权和资产维护权统一归 `Ops-Cli`
