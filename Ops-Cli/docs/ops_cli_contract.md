# Ops-Cli 调用规范

## 调用方式

统一从外部项目调用：

```bash
ops --json ...
```

不要再调用平台层散落脚本名。

## 约束

- 必须优先 `--json`
- 失败时以退出码非 0 表示
- `stdout` 只输出结果 JSON
- `stderr` 留给错误信息

## 标准结构

```json
{
  "success": true,
  "platform": "tmcs",
  "command": "bill download",
  "data": {}
}
```

推广账单下载同样遵守该结构：

```json
{
  "success": true,
  "platform": "tmcs",
  "command": "promotion-bill download",
  "data": {
    "sources": [],
    "downloaded_files": [],
    "failed": []
  }
}
```

推广账单文件名统一为 `智多星推广账单_YYYY-MM.xlsx` 和 `万象台推广账单_YYYY-MM.csv`；如果平台后续返回 Excel 二进制，Ops-Cli 会按真实内容自动保留 `.xlsx`。

## 外部编排项目应做什么

- 只负责组装业务参数
- 只负责记录业务日志
- 只负责读取 `success/platform/command/data`
- 不重新解析平台 Cookie / Token

## 外部编排项目不应做什么

- 不直接 import SessionHub 内部模块
- 不直接写平台 URL
- 不直接发平台 requests
- 不直接连 Playwright / CDP

## 兼容建议

- 外部项目保留原中文任务名
- 内部统一映射到 `ops ...`
- 只在业务层做自然语言触发，不在平台层做模糊任务分发
