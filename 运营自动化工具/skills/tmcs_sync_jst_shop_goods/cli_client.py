from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from config import OPS_BIN, OPS_CLI_ROOT


STANDARD_FIELDS = ["platform_item_id", "platform_sku_id", "supplier_goods_id", "merchant_goods_code"]


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _ops_command() -> list[str]:
    if not OPS_CLI_ROOT.exists():
        raise FileNotFoundError(f"Ops-Cli 项目路径不存在：{OPS_CLI_ROOT}")
    if OPS_BIN.exists():
        return [str(OPS_BIN)]
    raise FileNotFoundError(f"Ops-Cli 命令不存在：{OPS_BIN}。请先在 Ops-Cli 执行 pip install -e .")


def _run_ops(args: list[str]) -> Any:
    completed = subprocess.run([*_ops_command(), *args], cwd=OPS_CLI_ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Ops-Cli 执行失败：{completed.stderr.strip() or completed.stdout.strip()}")
    try:
        return json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ops-Cli 返回非 JSON：{completed.stdout[:500]}") from exc


def _standardize(row: dict[str, Any]) -> dict[str, str]:
    return {field: _text(row.get(field)) for field in STANDARD_FIELDS}


def query_tmcs_stock(*, item_ids: list[str], warehouse_code: str) -> list[dict[str, str]]:
    payload = _run_ops(
        [
            "tmcs",
            "stock",
            "query",
            "--item-ids",
            ",".join(item_ids),
            "--warehouse-code",
            warehouse_code,
            "--output",
            "json",
        ]
    )
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        payload = payload["data"]
    if not isinstance(payload, list):
        raise RuntimeError("Ops-Cli JSON 结构异常，tmcs stock query 期望返回数组。")
    return [_standardize(row) for row in payload if isinstance(row, dict)]


def learn_jst_shop_goods_import() -> dict[str, Any]:
    return _run_ops(["--json", "jst", "browser", "learn", "--scene", "shop-goods-import"])


def import_jst_shop_goods(*, file_path: str | Path, shop_name: str, mode: str = "ignore") -> dict[str, Any]:
    return _run_ops(
        [
            "--json",
            "jst",
            "shop-goods",
            "import",
            "--file",
            str(file_path),
            "--shop-name",
            shop_name,
            "--mode",
            mode,
            "--output",
            "json",
        ]
    )
