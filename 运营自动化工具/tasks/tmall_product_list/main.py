#!/usr/bin/env python3
"""Delegate TMCS product sync to Ops-Cli and keep the business entry stable."""

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


DEFAULT_WORK_DIR = get_path("maochao_work_dir")
DEFAULT_IMPORT_FILE = get_path("tmall_goods_import_file")
DEFAULT_SYNC_ROOT = get_path("ecommerce_brain_dir")
LATEST_FILE_NAME = get_path("tmall_goods_master_file")
JST_FILE_NAME = get_path("jst_product_master_file")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="更新猫超商品列表，并用聚水潭商品编码修正新增条码")
    parser.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR), help="保留参数兼容；实际由 Ops-Cli 读取其配置")
    parser.add_argument("--import-file", default=str(DEFAULT_IMPORT_FILE), help="保留参数兼容；实际由 Ops-Cli 读取其配置")
    parser.add_argument("--latest-file", default=str(LATEST_FILE_NAME), help="保留参数兼容")
    parser.add_argument("--jst-file", default=str(JST_FILE_NAME), help="保留参数兼容")
    parser.add_argument("--sync-root", default=str(DEFAULT_SYNC_ROOT), help="保留参数兼容")
    parser.add_argument("--skip-auto-download", action="store_true", help="不自动从猫超后台拉取商品列表，只读取现有导入表")
    parser.add_argument("--force-refresh", action="store_true", help="即使导入表已存在，也强制通过 Ops-Cli 重新拉取")
    parser.add_argument("--wait-login", dest="wait_login", action="store_true", default=True, help="保留参数兼容")
    parser.add_argument("--no-wait-login", dest="wait_login", action="store_false", help="保留参数兼容")
    parser.add_argument("--auto-capture", dest="auto_capture", action="store_true", default=True, help="保留参数兼容")
    parser.add_argument("--no-auto-capture", dest="auto_capture", action="store_false", help="保留参数兼容")
    parser.add_argument("--page-size", type=int, default=100, help="保留参数兼容")
    parser.add_argument("--sync-all", action=argparse.BooleanOptionalAction, default=True, help="保留参数兼容")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写入主表")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = ["--json", "tmcs", "product", "sync"]
    if args.dry_run:
        command.append("--dry-run")
    if args.skip_auto_download:
        command.append("--use-local-only")
    if args.force_refresh:
        command.append("--force-refresh")

    payload = run_ops_json(command)
    data = payload.get("data") if isinstance(payload, dict) else {}
    result = {
        "success": bool(payload.get("success")),
        "task": "update_maochao_goods",
        "platform": payload.get("platform"),
        "command": payload.get("command"),
        "dry_run": args.dry_run,
        "force_refresh": args.force_refresh,
        "use_local_only": args.skip_auto_download,
        "ops_result": payload,
        "import_file": data.get("import_file") if isinstance(data, dict) else None,
        "latest_file": data.get("latest_file") if isinstance(data, dict) else None,
        "sync_summary": data.get("sync_summary") if isinstance(data, dict) else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
