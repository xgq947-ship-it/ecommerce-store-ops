#!/usr/bin/env python3
"""Delegate JST product sync to Ops-Cli and keep the business entry stable."""

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


DEFAULT_KEEP_BRANDS = ("奥克斯", "苏泊尔")
DEFAULT_SOURCE = get_path("jst_product_import_file")
DEFAULT_ROOT = get_path("ecommerce_brain_dir")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="更新电商Brain内所有聚水潭商品资料")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="保留参数兼容；实际由 Ops-Cli 读取其配置")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="保留参数兼容；实际由 Ops-Cli 递归同步")
    parser.add_argument("--keep-brands", nargs="+", default=list(DEFAULT_KEEP_BRANDS), help="要保留的品牌")
    parser.add_argument("--no-filter", action="store_true", help="保留参数兼容；当前会透传空品牌列表给 Ops-Cli")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不覆盖")
    parser.add_argument("--use-local-only", action="store_true", help="只使用本地现成源文件，不自动从聚水潭后台导出下载")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = ["--json", "jst", "product", "sync"]
    if args.dry_run:
        command.append("--dry-run")
    if args.use_local_only:
        command.append("--use-local-only")
    if not args.no_filter:
        if args.keep_brands:
            command.extend(["--keep-brands", args.keep_brands[0], *args.keep_brands[1:]])

    payload = run_ops_json(command)
    data = payload.get("data") if isinstance(payload, dict) else {}
    result = {
        "success": bool(payload.get("success")),
        "task": "update_jst_products",
        "platform": payload.get("platform"),
        "command": payload.get("command"),
        "source": str(args.source),
        "root": str(args.root),
        "keep_brands": [] if args.no_filter else list(args.keep_brands),
        "ops_result": payload,
        "latest_file": data.get("latest_file") if isinstance(data, dict) else None,
        "import_file": data.get("import_file") if isinstance(data, dict) else None,
        "targets": data.get("targets") if isinstance(data, dict) else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
