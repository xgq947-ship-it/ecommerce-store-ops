# 9222 浏览器调试说明

## 定位

`9222` 只服务于 SessionHub 专用浏览器。

- 用于 `ensure / capture / recheck`
- 用于长期稳定执行
- 不用于主浏览器探测

## 快速检查

```bash
ops --json browser check --port 9222
```

## 使用原则

- 9222 profile 固定隔离
- 平台登录后由 Ops-Cli / SessionHub 复用
- 业务脚本不能直接读取 9222 会话文件

## 推荐恢复方式

先确认端口：

```bash
ops --json browser check --port 9222
```

再执行对应平台命令：

```bash
ops --json tmcs auth ensure
ops --json jst auth ensure
```

## 当前兼容路径

当前 `SESSIONHUB_ROOT` 默认指向：

```text
/Users/dasheng/Desktop/电商Brain/02-运营店铺/Ops-Cli/sessionhub
```

这只是会话资产目录，不代表平台逻辑仍归业务项目。
