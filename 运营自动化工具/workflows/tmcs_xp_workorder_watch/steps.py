"""猫超 XP 工单监控 workflow 的 step handler。

业务层只通过 clients.ops_cli_client.run_ops_json 调用 Ops-Cli，
不写猫超 URL、Cookie、Selector、Playwright、CDP。

dry-run 安全点：
- fetch 步骤向 Ops-Cli 透传 --dry-run，平台层返回 simulated=true，不请求真实猫超。
- 不发送任何通知；--notify 仅作占位预留，第一版输出 TODO。
"""

from __future__ import annotations

import argparse
from typing import Any

from clients.ops_cli_client import run_ops_json
from core.runtime import StepContext, failure_result, success_result


DEFAULT_THRESHOLD = 4


def _parse_flags(ctx: StepContext) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    parser.add_argument("--notify", action="store_true")
    parser.add_argument("--json", action="store_true")
    namespace, _ = parser.parse_known_args(ctx.inputs.get("args") or [])
    namespace.dry_run = ctx.dry_run or namespace.dry_run
    return namespace


def check_inputs(ctx: StepContext):
    flags = _parse_flags(ctx)
    if flags.threshold < 0:
        return failure_result(errors=[f"threshold 必须为非负整数，收到 {flags.threshold}"])
    ctx.state["flags"] = flags
    return success_result(
        outputs={
            "dry_run": flags.dry_run,
            "threshold": flags.threshold,
            "notify_requested": flags.notify,
        }
    )


def fetch_workorder_count(ctx: StepContext):
    flags = ctx.state["flags"]
    command = [
        "--json",
        "tmcs",
        "xp-workorder",
        "count",
        "--threshold",
        str(flags.threshold),
    ]
    if flags.dry_run:
        command.append("--dry-run")
    try:
        payload = run_ops_json(command, interactive_recovery=not flags.dry_run)
    except RuntimeError as exc:
        return failure_result(errors=[f"Ops-Cli 调用失败：{exc}"])

    data: dict[str, Any] = payload.get("data") or {}
    if "count" not in data:
        return failure_result(errors=[f"Ops-Cli 返回缺少 count 字段：{data}"])
    ctx.state["ops_data"] = data
    return success_result(
        outputs={
            "count": int(data.get("count", 0)),
            "source": data.get("source"),
            "simulated": bool(data.get("simulated", False)),
            "scene": data.get("scene"),
            "ops_context_path": data.get("context_path"),
        }
    )


def evaluate_threshold(ctx: StepContext):
    flags = ctx.state["flags"]
    data = ctx.state["ops_data"]
    count = int(data.get("count", 0))
    threshold = int(data.get("threshold", flags.threshold))
    exceeded = count > threshold
    if exceeded:
        message = f"当前猫超 XP 工单数量：{count}，已超过阈值 {threshold}"
    else:
        message = f"当前猫超 XP 工单数量：{count}，未超过阈值 {threshold}"
    ctx.state["count"] = count
    ctx.state["threshold"] = threshold
    ctx.state["exceeded"] = exceeded
    ctx.state["message"] = message
    return success_result(
        outputs={
            "count": count,
            "threshold": threshold,
            "exceeded": exceeded,
            "message": message,
        }
    )


def collect_outputs(ctx: StepContext):
    flags = ctx.state["flags"]
    data = ctx.state.get("ops_data") or {}
    if flags.notify:
        notification = {"sent": False, "reason": "TODO 通知尚未实装，预留 --notify 参数。"}
    else:
        notification = {"sent": False, "reason": "通知未启用"}
    return success_result(
        outputs={
            "task": "tmcs_xp_workorder_watch",
            "dry_run": flags.dry_run,
            "count": ctx.state.get("count"),
            "threshold": ctx.state.get("threshold"),
            "exceeded": ctx.state.get("exceeded"),
            "message": ctx.state.get("message"),
            "source": data.get("source"),
            "simulated": bool(data.get("simulated", False)),
            "scene": data.get("scene"),
            "ops_context_path": data.get("context_path"),
            "notification": notification,
        }
    )
