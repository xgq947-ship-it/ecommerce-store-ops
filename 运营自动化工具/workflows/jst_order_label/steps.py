"""聚水潭刷单订单打标 workflow 的 step handler。

复用 tasks/jst_order_label/main.py 的平台调用（run_ops_json）与默认输入路径，不重写
打标逻辑，也不直接请求平台（仍经 clients/ops_cli_client.py -> Ops-Cli）。

dry-run 安全点：dry-run 永不追加 --execute（Ops-Cli label 不带 --execute 即只查询/预览），
且 interactive_recovery=False。真实插黄旗必须非 dry-run（追加 --execute）。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from core.runtime import StepContext, failure_result, success_result

import tasks.jst_order_label.main as legacy


def _parse_flags(ctx: StepContext) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--order-id", action="append", default=[])
    parser.add_argument("--input", default=str(legacy.INPUT_PATH))
    parser.add_argument("--limit", type=int, default=None)
    namespace, _ = parser.parse_known_args(ctx.inputs.get("args") or [])
    namespace.dry_run = ctx.dry_run or namespace.dry_run
    return namespace


def _build_command(flags: argparse.Namespace, *, execute: bool) -> list[str]:
    command = ["--json", "jst", "order", "label"]
    if flags.order_id:
        for order_id in flags.order_id:
            command.extend(["--order-id", order_id])
    else:
        command.extend(["--input", str(Path(flags.input).expanduser().resolve())])
    if flags.limit is not None:
        command.extend(["--limit", str(flags.limit)])
    if execute:
        command.append("--execute")
    return command


def _summarize(payload: dict) -> dict:
    data = payload.get("data") if isinstance(payload, dict) else {}
    data = data if isinstance(data, dict) else {}
    return {
        "success": bool(payload.get("success")) if isinstance(payload, dict) else False,
        "failed_file": data.get("failed_file"),
        "runtime_context": data.get("runtime_context"),
    }


def check_inputs(ctx: StepContext):
    flags = _parse_flags(ctx)
    ctx.state["flags"] = flags
    return success_result(
        outputs={
            "dry_run": flags.dry_run,
            "order_ids": list(flags.order_id),
            "input": str(Path(flags.input).expanduser().resolve()),
            "limit": flags.limit,
        }
    )


def load_orders(ctx: StepContext):
    flags = ctx.state["flags"]
    source = "order_id" if flags.order_id else "input_file"
    return success_result(
        outputs={
            "order_source": source,
            "order_id_count": len(flags.order_id),
            "input": None if flags.order_id else str(Path(flags.input).expanduser().resolve()),
        }
    )


def preview_labels(ctx: StepContext):
    flags = ctx.state["flags"]
    if not flags.dry_run:
        return success_result(outputs={"skipped": True, "reason": "真实执行直接走 apply_labels"})
    command = _build_command(flags, execute=False)
    payload = legacy.run_ops_json(command, interactive_recovery=False)
    ctx.state["payload"] = payload
    return success_result(outputs={"preview": True, **_summarize(payload)})


def apply_labels(ctx: StepContext):
    flags = ctx.state["flags"]
    if flags.dry_run:
        return success_result(outputs={"skipped": True, "reason": "dry-run 不执行真实打标（不加 --execute）"})
    command = _build_command(flags, execute=True)
    payload = legacy.run_ops_json(command, interactive_recovery=True)
    ctx.state["payload"] = payload
    return success_result(outputs={"executed": True, **_summarize(payload)})


def collect_outputs(ctx: StepContext):
    flags = ctx.state["flags"]
    payload = ctx.state.get("payload") or {}
    summary = _summarize(payload)
    return success_result(
        outputs={
            "task": "tag_jst_brush_orders",
            "dry_run": flags.dry_run,
            "order_ids": list(flags.order_id),
            "limit": flags.limit,
            **summary,
        }
    )
