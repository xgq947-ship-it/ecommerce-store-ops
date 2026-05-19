---
name: ecommerce-operations-automation
description: Use when the user mentions recurring local ecommerce operations in /Users/dasheng/Desktop/电商Brain, including semantically similar wording for 刷单登记, 猫超账单/对账, 猫超商品列表, 聚水潭商品资料, 买家秀, 公司网盘/NAS产品资料, 上架数据, or asks to run or extend the shared run.py automation entry point.
---

# 运营自动化工具 Skill

这个 skill 只维护业务编排层：

```text
/Users/dasheng/Desktop/电商Brain/02-运营店铺/运营自动化工具
```

## 核心边界

- 允许：
  - `run.py`
  - `tasks/`
  - Excel 处理
  - 业务规则
  - 上下文 / retry / 日志
  - `subprocess` 调 `ops --json ...`
- 禁止：
  - 平台 URL
  - Cookie / Token
  - requests 直连平台
  - Playwright / CDP / 浏览器页面操作
  - Selector
  - 直接 import `sessionhub/*`

## 新任务规则

1. 新任务先放 `tasks/`
2. 在 `core/task_registry.py` 注册任务名与 aliases
3. 优先接 `run.py`
4. 平台动作统一放到 `Ops-Cli`
5. 业务层通过 `clients/ops_cli_client.py` 调 `ops --json ...`
6. 更新 `README.md`、`SKILL.md`、相关 `skill.yaml`

## 平台调用规则

业务任务应调用：

```bash
ops --json ...
```

不要调用：

```bash
python sessionhub.py ...
python demo.py ...
python browser_test.py ...
```

## 当前已同步的关键任务

- `更新聚水潭资料` -> `ops --json jst product sync`
- `更新猫超商品列表` -> `ops --json tmcs product sync`
- `刷单订单插黄旗` -> `ops --json jst order label`
- `刷单报销登记` -> `ops --json jst order reimburse`
- `猫超账单下载阶段` -> `ops --json tmcs bill download`

## 触发方式

保留模糊触发，不要求精准匹配。

- `刷单表格登记`
- `刷单订单插黄旗`
- `更新聚水潭资料`
- `更新猫超商品列表`
- `猫超账单整理`
- `买家秀打包`
- `更新公司网盘索引`

## 文档同步要求

每次改入口或边界，都要同步：

- 根目录 `README.md`
- 当前 `SKILL.md`
- 对应任务 `README.md`
- `docs/` 下的架构 / 边界 / 调用规范
- 对应 `skill.yaml`
