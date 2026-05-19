from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from cli_client import import_jst_shop_goods, learn_jst_shop_goods_import, query_tmcs_stock
from config import DEFAULT_JST_SHOP_NAME, DEFAULT_WAREHOUSE_CODE, LOG_DIR, OUTPUT_DIR, ensure_dirs
from excel_builder import build_import_workbooks, build_rows
from input_loader import resolve_item_ids


def _setup_logger(timestamp: str) -> Path:
    ensure_dirs()
    log_path = LOG_DIR / f"tmcs_sync_jst_shop_goods_{timestamp}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler(sys.stderr)],
        force=True,
    )
    return log_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="将猫超商品信息同步到聚水潭店铺商品资料。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    learn = subparsers.add_parser("learn", help="学习聚水潭导入入口和浏览器登录态。")
    learn.add_argument("--timeout", type=int, default=90, help="监听主浏览器请求的秒数。")

    run = subparsers.add_parser("run", help="查询猫超库存，生成聚水潭导入 Excel，可选自动导入。")
    run.add_argument("--item-ids", help="多个平台商品ID，用英文逗号分隔。")
    run.add_argument("--input-file", help="包含平台商品ID的 Excel 文件。")
    run.add_argument("--warehouse-code", default=DEFAULT_WAREHOUSE_CODE, help="商家仓 code。")
    run.add_argument("--shop-name", default=DEFAULT_JST_SHOP_NAME, help="聚水潭店铺名称，透传给 Ops-Cli。")
    run.add_argument("--import-mode", default="ignore", choices=["ignore", "cover"], help="聚水潭导入模式。")
    import_group = run.add_mutually_exclusive_group()
    import_group.add_argument("--import-jst", action="store_true", help="生成 Excel 后自动导入聚水潭。")
    import_group.add_argument("--no-import", action="store_true", help="只生成 Excel，不导入聚水潭。")
    return parser


def _run(args: argparse.Namespace, timestamp: str, log_path: Path) -> int:
    item_ids = resolve_item_ids(item_ids=args.item_ids, input_file=args.input_file)
    logging.info("读取商品ID完成：%s", item_ids)

    stock_rows = query_tmcs_stock(item_ids=item_ids, warehouse_code=args.warehouse_code)
    logging.info("Ops-Cli 返回库存行数：%s", len(stock_rows))

    import_rows, failures = build_rows(requested_item_ids=item_ids, stock_rows=stock_rows)
    workbook_result = build_import_workbooks(
        import_rows=import_rows,
        failures=failures,
        output_dir=OUTPUT_DIR,
        timestamp=timestamp,
    )
    logging.info("生成导入 Excel：%s", workbook_result["import_path"])
    if workbook_result.get("failed_path"):
        logging.info("生成失败 Excel：%s", workbook_result["failed_path"])

    import_result = None
    if args.import_jst:
        if not import_rows:
            raise RuntimeError("没有有效数据可导入聚水潭，已生成失败数据。")
        logging.info("通过 Ops-Cli 执行聚水潭店铺商品导入。")
        import_result = import_jst_shop_goods(
            file_path=str(workbook_result["import_path"]),
            shop_name=args.shop_name,
            mode=args.import_mode,
        )
        logging.info("聚水潭导入结果：%s", import_result)

    result = {
        "success": True,
        "item_ids": item_ids,
        "warehouse_code": args.warehouse_code,
        "stock_rows": len(stock_rows),
        "import_rows": workbook_result["import_rows"],
        "failed_rows": workbook_result["failed_rows"],
        "import_path": workbook_result["import_path"],
        "failed_path": workbook_result["failed_path"],
        "import_jst": bool(args.import_jst),
        "import_mode": args.import_mode,
        "import_result": import_result,
        "log_path": str(log_path),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _learn(args: argparse.Namespace, log_path: Path) -> int:
    logging.info("通过 Ops-Cli 执行聚水潭浏览器 learn。")
    payload = learn_jst_shop_goods_import()
    data = payload.get("data") if isinstance(payload, dict) else {}
    result = {
        "success": True,
        "ops_cli_result": payload,
        "profile_path": data.get("profile_path") if isinstance(data, dict) else None,
        "page_url": data.get("page_url") if isinstance(data, dict) else None,
        "page_title": data.get("page_title") if isinstance(data, dict) else None,
        "log_path": str(log_path),
        "next": {
            "check_9222": "ops --json browser check --port 9222",
            "run": "python skills/tmcs_sync_jst_shop_goods/main.py run --item-ids 123456,234567 --import-jst --import-mode cover",
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = _setup_logger(timestamp)
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "learn":
            return _learn(args, log_path)
        if args.command == "run":
            return _run(args, timestamp, log_path)
        raise RuntimeError(f"未知命令：{args.command}")
    except Exception as exc:
        logging.exception("执行失败：%s", exc)
        print(json.dumps({"success": False, "error": str(exc), "log_path": str(log_path)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
