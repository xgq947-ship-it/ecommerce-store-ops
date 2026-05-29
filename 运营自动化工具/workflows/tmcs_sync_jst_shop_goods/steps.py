"""猫超商品信息同步聚水潭 workflow 的 step handler。

复用 skills/tmcs_sync_jst_shop_goods 下的成熟实现（input_loader / cli_client /
excel_builder / config），不重写商品映射、Excel 生成或平台调用逻辑，也不直接请求平台
（仍经 clients/ops_cli_client.py -> Ops-Cli）。

旧 skill 不支持 --dry-run，且必须传 --item-ids/--input-file 才能查询。因此本 workflow 的
dry-run 是「安全预览」：只解析输入，不查询真实平台、不生成 Excel、不导入聚水潭。
真实导入仍沿用 skill 策略，必须显式 --import-jst。
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from core.runtime import Artifact, StepContext, failure_result, success_result

_SKILL_DIR = Path(__file__).resolve().parents[1].parent / "skills" / "tmcs_sync_jst_shop_goods"
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

import cli_client  # noqa: E402
import config as skill_config  # noqa: E402
import excel_builder  # noqa: E402
import input_loader  # noqa: E402


def _parse_flags(ctx: StepContext) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--item-ids", default=None)
    parser.add_argument("--input-file", default=None)
    parser.add_argument("--warehouse-code", default=skill_config.DEFAULT_WAREHOUSE_CODE)
    parser.add_argument("--shop-name", default=skill_config.DEFAULT_JST_SHOP_NAME)
    parser.add_argument("--import-mode", default="ignore", choices=["ignore", "cover"])
    parser.add_argument("--import-jst", action="store_true")
    parser.add_argument("--no-import", action="store_true")
    namespace, _ = parser.parse_known_args(ctx.inputs.get("args") or [])
    namespace.dry_run = ctx.dry_run or namespace.dry_run
    return namespace


def check_inputs(ctx: StepContext):
    flags = _parse_flags(ctx)
    ctx.state["flags"] = flags
    return success_result(
        outputs={
            "dry_run": flags.dry_run,
            "warehouse_code": flags.warehouse_code,
            "shop_name": flags.shop_name,
            "import_mode": flags.import_mode,
            "import_jst": flags.import_jst,
            "has_item_ids": bool(flags.item_ids or flags.input_file),
        }
    )


def load_tmcs_goods(ctx: StepContext):
    flags = ctx.state["flags"]
    if not (flags.item_ids or flags.input_file):
        if ctx.dry_run:
            return success_result(
                outputs={
                    "skipped": True,
                    "reason": "未提供 --item-ids/--input-file；真实执行需要其一",
                    "item_id_count": 0,
                }
            )
        return failure_result("没有输入商品ID。请使用 --item-ids 或 --input-file。")
    item_ids = input_loader.resolve_item_ids(item_ids=flags.item_ids, input_file=flags.input_file)
    ctx.state["item_ids"] = item_ids
    return success_result(outputs={"item_id_count": len(item_ids), "item_ids": item_ids})


def query_tmcs_stock(ctx: StepContext):
    flags = ctx.state["flags"]
    item_ids = ctx.state.get("item_ids") or []
    if ctx.dry_run:
        return success_result(
            outputs={
                "skipped": True,
                "reason": "dry-run 不查询真实平台",
                "would_query_item_ids": len(item_ids),
            }
        )
    if not item_ids:
        return failure_result("没有可查询的商品ID")
    stock_rows = cli_client.query_tmcs_stock(item_ids=item_ids, warehouse_code=flags.warehouse_code)
    ctx.state["stock_rows"] = stock_rows
    return success_result(outputs={"stock_rows": len(stock_rows)})


def build_jst_import_excel(ctx: StepContext):
    flags = ctx.state["flags"]
    if ctx.dry_run:
        return success_result(outputs={"skipped": True, "reason": "dry-run 不生成导入 Excel"})

    item_ids = ctx.state["item_ids"]
    stock_rows = ctx.state["stock_rows"]
    import_rows, failures = excel_builder.build_rows(requested_item_ids=item_ids, stock_rows=stock_rows)
    skill_config.ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    workbook_result = excel_builder.build_import_workbooks(
        import_rows=import_rows,
        failures=failures,
        output_dir=skill_config.OUTPUT_DIR,
        timestamp=timestamp,
    )
    ctx.state["workbook_result"] = workbook_result
    ctx.state["import_rows"] = import_rows

    artifacts = [
        Artifact(
            type="xlsx",
            role="import",
            name=Path(workbook_result["import_path"]).name,
            path=str(workbook_result["import_path"]),
            platform="jst",
        )
    ]
    if workbook_result.get("failed_path"):
        artifacts.append(
            Artifact(
                type="xlsx",
                role="failed",
                name=Path(workbook_result["failed_path"]).name,
                path=str(workbook_result["failed_path"]),
                platform="jst",
            )
        )
    return success_result(
        outputs={
            "import_path": str(workbook_result["import_path"]),
            "failed_path": str(workbook_result["failed_path"]) if workbook_result.get("failed_path") else None,
            "import_rows": workbook_result["import_rows"],
            "failed_rows": workbook_result["failed_rows"],
        },
        artifacts=artifacts,
    )


def import_jst_shop_goods(ctx: StepContext):
    flags = ctx.state["flags"]
    if ctx.dry_run:
        return success_result(outputs={"skipped": True, "reason": "dry-run 不导入聚水潭"})
    if not flags.import_jst:
        return success_result(outputs={"imported": False, "reason": "未启用导入（需 --import-jst）"})

    import_rows = ctx.state.get("import_rows") or []
    if not import_rows:
        return failure_result("没有有效数据可导入聚水潭，已生成失败数据。")
    workbook_result = ctx.state["workbook_result"]
    import_result = cli_client.import_jst_shop_goods(
        file_path=str(workbook_result["import_path"]),
        shop_name=flags.shop_name,
        mode=flags.import_mode,
    )
    ctx.state["import_result"] = import_result
    return success_result(outputs={"imported": True, "import_result": import_result})


def collect_artifacts(ctx: StepContext):
    flags = ctx.state["flags"]
    workbook_result = ctx.state.get("workbook_result") or {}
    return success_result(
        outputs={
            "task": "tmcs_sync_jst_shop_goods",
            "dry_run": flags.dry_run,
            "item_id_count": len(ctx.state.get("item_ids") or []),
            "import_path": str(workbook_result["import_path"]) if workbook_result.get("import_path") else None,
            "import_jst": bool(flags.import_jst),
            "imported": ctx.state.get("import_result") is not None,
        }
    )
