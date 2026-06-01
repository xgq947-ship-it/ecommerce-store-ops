# tmcs_xp_workorder_watch — 猫超 XP 工单数量监控

## 用途

读取猫超后台「XP 工单处理」当前待处理工单数量，与阈值比较。超过阈值时输出告警文案；否则输出当前数量与"无需处理"状态。第一版不真正推送通知（仅占位）。

## 调用链

```
run.py workflow tmcs_xp_workorder_watch
  └─ workflows/tmcs_xp_workorder_watch/workflow.py
       └─ clients/ops_cli_client.run_ops_json
            └─ ops --json tmcs xp-workorder count --threshold N [--dry-run]
                 └─ Ops-Cli tmcs/xp_workorder.py  (scene: tmall_chaoshi/xp_workorder_count)
```

平台 URL/Cookie/Selector/Playwright/CDP 全部封装在 Ops-Cli；business 层只消费 JSON。

## 参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--threshold` | `4` | 工单数量阈值，`count > threshold` 视为超过 |
| `--dry-run` | False | 安全预览：Ops-Cli 不读 scene、不请求平台，返回 simulated=true |
| `--notify` | False | 预留参数，第一版不真实推送，输出 TODO |
| `--json` | False | 仅占位，run.py 不消费 |

## 步骤

| step | 行为 | dry-run 行为 |
|---|---|---|
| `check_inputs` | 解析 `--threshold/--dry-run/--notify` | 同实模式 |
| `fetch_workorder_count` | 调 `ops --json tmcs xp-workorder count` | 透传 `--dry-run`，Ops-Cli 返回 simulated=true、count=0 |
| `evaluate_threshold` | 计算 `exceeded = count > threshold`，生成中文文案 | 同实模式（基于模拟数量） |
| `collect_outputs` | 汇总最终输出 | 标记 `dry_run=true, simulated=true`；notification 永远不发送 |

## 输出字段（最终 step）

```jsonc
{
  "task": "tmcs_xp_workorder_watch",
  "dry_run": true,
  "count": 0,
  "threshold": 4,
  "exceeded": false,
  "message": "当前猫超 XP 工单数量：0，未超过阈值 4",
  "source": "simulated",        // simulated | api
  "simulated": true,
  "scene": "tmall_chaoshi/xp_workorder_count",
  "ops_context_path": "...",
  "notification": {"sent": false, "reason": "通知未启用"}
}
```

## 边界

- 不直接打猫超 URL，不读 Cookie/Token，不写 Playwright/CDP。
- 不修改 session/cookie/token 文件。
- dry-run 绝不发送企微/微信、不处理工单、不写 Excel。
- 失败语义：`fetch_workorder_count` 失败即终止 workflow，输出 `errors`。

## scene 学习

如 scene 不存在或登录态失效：

```bash
ops --json --interactive-login tmcs xp-workorder learn [--force]
```

在交互终端运行，按提示在主浏览器登录猫超并进入「XP 工单处理」页，由 SessionHub 抓取列表接口结构。
