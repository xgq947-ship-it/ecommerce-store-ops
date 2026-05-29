"""更新猫超商品列表 workflow 的 step handler。

复用 tasks/tmall_product_list/main.py 的平台调用（run_ops_json -> ops tmcs product sync），
不重写商品同步逻辑，也不直接请求平台。猫超商品同步在 Ops-Cli 内部一次完成下载/校验/写主表，
本 workflow 用一次平台调用承载，其余步骤围绕它做检查与汇报。

dry-run 安全点：向 ops 透传 --dry-run，Ops-Cli 只预览、不写主表/最新表；interactive_recovery
由公共客户端按 --dry-run 自动判定为 False，不拉起浏览器。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from core.runtime import Artifact, StepContext, failure_result, success_result

import tasks.tmall_product_list.main as legacy


def _parse_flags(ctx: StepContext) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-auto-download", action="store_true")
    parser.add_argument("--force-refresh", action="store_true")
    namespace, _ = parser.parse_known_args(ctx.inputs.get("args") or [])
    namespace.dry_run = ctx.dry_run or namespace.dry_run
    return namespace


def _data(ctx: StepContext) -> dict:
    payload = ctx.state.get("payload") or {}
    data = payload.get("data") if isinstance(payload, dict) else {}
    return data if isinstance(data, dict) else {}


def check_inputs(ctx: StepContext):
    flags = _parse_flags(ctx)
    ctx.state["flags"] = flags
    return success_result(
        outputs={
            "dry_run": flags.dry_run,
            "use_local_only": flags.skip_auto_download,
            "force_refresh": flags.force_refresh,
        }
    )


def check_local_source(ctx: StepContext):
    import_file = Path(str(legacy.DEFAULT_IMPORT_FILE)).expanduser()
    ctx.state["import_file"] = import_file
    return success_result(outputs={"import_file": str(import_file), "import_file_exists": import_file.exists()})


def download_tmcs_products(ctx: StepContext):
    flags = ctx.state["flags"]
    command = ["--json", "tmcs", "product", "sync"]
    if flags.dry_run:
        command.append("--dry-run")
    if flags.skip_auto_download:
        command.append("--use-local-only")
    if flags.force_refresh:
        command.append("--force-refresh")
    try:
        payload = legacy.run_ops_json(command)
    except Exception as exc:  # noqa: BLE001 - dry-run 容忍平台/数据未就绪，降级为安全预览
        if flags.dry_run:
            ctx.state["no_sync"] = True
            return success_result(outputs={"skipped": True, "reason": str(exc)})
        return failure_result(str(exc))
    ctx.state["payload"] = payload
    data = payload.get("data") if isinstance(payload, dict) else {}
    data = data if isinstance(data, dict) else {}
    return success_result(
        outputs={
            "success": bool(payload.get("success")) if isinstance(payload, dict) else False,
            "command": payload.get("command") if isinstance(payload, dict) else None,
            "import_file": data.get("import_file"),
        }
    )


def validate_products(ctx: StepContext):
    data = _data(ctx)
    return success_result(outputs={"sync_summary": data.get("sync_summary")})


def update_master_data(ctx: StepContext):
    flags = ctx.state["flags"]
    data = _data(ctx)
    if flags.dry_run:
        return success_result(
            outputs={"skipped": True, "reason": "dry-run：Ops-Cli 仅预览，未写主表/最新表", "latest_file": data.get("latest_file")}
        )
    return success_result(outputs={"latest_file": data.get("latest_file"), "written": True})


def collect_artifacts(ctx: StepContext):
    flags = ctx.state["flags"]
    data = _data(ctx)
    artifacts = []
    latest_file = data.get("latest_file")
    if not flags.dry_run and latest_file and Path(str(latest_file)).exists():
        artifacts.append(
            Artifact(type="xlsx", role="master_latest", name=Path(str(latest_file)).name, path=str(latest_file), platform="tmcs")
        )
    return success_result(
        outputs={
            "task": "update_maochao_goods",
            "dry_run": flags.dry_run,
            "import_file": data.get("import_file"),
            "latest_file": latest_file,
            "sync_summary": data.get("sync_summary"),
        },
        artifacts=artifacts,
    )
