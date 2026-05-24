#!/usr/bin/env python3
"""Delegate JST order labeling to Ops-Cli and keep the business entry stable."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clients.ops_cli_client import run_ops_json  # noqa: E402
from core.config_loader import get_path  # noqa: E402


INPUT_PATH = get_path("runtime_dir") / "latest_brush_orders.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="聚水潭刷单订单打标")
    parser.add_argument("--order-id", action="append", default=[], help="订单号，可重复传入")
    parser.add_argument("--input", default=str(INPUT_PATH), help="订单号 JSON 输入文件")
    parser.add_argument("--dry-run", action="store_true", help="只查询订单，不执行备注和标签")
    parser.add_argument("--limit", type=int, help="只处理前 N 单")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = [
        "--json",
        "jst",
        "order",
        "label",
    ]
    if args.order_id:
        for order_id in args.order_id:
            command.extend(["--order-id", order_id])
    else:
        command.extend(["--input", str(Path(args.input).expanduser().resolve())])
    if args.limit is not None:
        command.extend(["--limit", str(args.limit)])
    if not args.dry_run:
        command.append("--execute")

    payload = run_ops_json(command, interactive_recovery=not args.dry_run)
    data = payload.get("data") if isinstance(payload, dict) else {}
    result = {
        "success": bool(payload.get("success")),
        "task": "tag_jst_brush_orders",
        "platform": payload.get("platform"),
        "command": payload.get("command"),
        "dry_run": args.dry_run,
        "limit": args.limit,
        "order_ids": list(args.order_id),
        "input": str(Path(args.input).expanduser().resolve()),
        "ops_result": payload,
        "failed_file": data.get("failed_file") if isinstance(data, dict) else None,
        "runtime_context": data.get("runtime_context") if isinstance(data, dict) else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
