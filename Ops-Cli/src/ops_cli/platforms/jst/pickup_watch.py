from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ops_cli.output import CommandResponse


CONFIG_PATH = Path("data/jst/pickup_watch_config.json")


def _load_keywords() -> list[str]:
    env_value = os.getenv("JST_PICKUP_WATCH_KEYWORDS", "").strip()
    if env_value:
        return [item.strip() for item in env_value.split(",") if item.strip()]
    path = Path.cwd() / CONFIG_PATH
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        values = payload.get("pickup_keywords") or []
        if isinstance(values, list):
            return [str(item).strip() for item in values if str(item).strip()]
    raise RuntimeError(f"揽收关键词配置缺失：{path}")


def _trace_text(event: Any) -> str:
    if isinstance(event, dict):
        return " ".join(str(value) for value in event.values() if value is not None)
    return str(event or "")


def detect_pickup_record(traces: list[Any], keywords: list[str] | None = None) -> tuple[bool, str]:
    matched_keywords = keywords if keywords is not None else _load_keywords()
    trace_text = "\n".join(_trace_text(event) for event in traces)
    for keyword in matched_keywords:
        if keyword and keyword in trace_text:
            return True, keyword
    return False, ""


def _order(
    *,
    now: datetime,
    suffix: str,
    hours_ago: float,
    platform: str = "天猫超市",
    logistics_no: str = "",
    traces: list[dict[str, str]] | None = None,
    status: str = "",
) -> dict[str, Any]:
    trace_items = traces or []
    picked_up, keyword = detect_pickup_record(trace_items)
    pay_time = now - timedelta(hours=hours_ago)
    return {
        "shop_name": "dry-run 猫超店铺" if "猫超" in platform else "dry-run 其他店铺",
        "platform_order_no": f"DRY-PLATFORM-{suffix}",
        "jst_order_no": f"DRY-JST-{suffix}",
        "platform": platform,
        "order_source": platform,
        "jst_pay_time": pay_time.isoformat(timespec="seconds"),
        "maochao_real_pay_time": "",
        "logistics_company": "顺丰速运",
        "logistics_no": logistics_no,
        "latest_logistics_status": status,
        "logistics_traces": trace_items,
        "has_pickup_record": picked_up,
        "pickup_matched_keyword": keyword,
        "raw": {"dry_run_case": suffix},
    }


def _dry_run_orders(now: datetime) -> list[dict[str, Any]]:
    today_after_stop = now.replace(hour=17, minute=45, second=0, microsecond=0)
    rows = [
        _order(
            now=now,
            suffix="PICKED",
            hours_ago=26,
            logistics_no="SFDRY001",
            status="运输中",
            traces=[{"time": now.isoformat(timespec="seconds"), "content": "快件已由顺丰收取"}],
        ),
        _order(now=now, suffix="NORMAL", hours_ago=6),
        _order(now=now, suffix="REMIND", hours_ago=13, logistics_no="SFDRY003"),
        _order(now=now, suffix="HIGH", hours_ago=21, logistics_no="SFDRY004"),
        _order(now=now, suffix="TIMEOUT", hours_ago=25),
        _order(now=now, suffix="MAOCHAO-OFFSET", hours_ago=19.75),
        _order(now=now, suffix="NO-TRACE", hours_ago=14, logistics_no="SFDRY007"),
        _order(
            now=now,
            suffix="TRACE-NO-PICKUP",
            hours_ago=22,
            logistics_no="SFDRY008",
            status="已发货",
            traces=[{"time": now.isoformat(timespec="seconds"), "content": "运单已创建，待快递收件"}],
        ),
    ]
    rows.append(
        {
            **_order(now=now, suffix="AFTER-1730", hours_ago=0.0, platform="其他平台"),
            "jst_pay_time": today_after_stop.isoformat(timespec="seconds"),
        }
    )
    return rows


def _fetch_paid_orders(*, hours: int, shop_name: str | None, debug: bool) -> list[dict[str, Any]]:
    del hours, shop_name, debug
    raise RuntimeError(
        "聚水潭揽收监控真实查询尚缺少已验证的近 48 小时付款订单及轨迹 scene；"
        "请先学习并补齐 order pickup-watch 字段映射。当前可使用 --dry-run 验证完整业务流程。"
    )


def run_pickup_watch(
    *,
    hours: int = 48,
    shop_name: str | None = None,
    dry_run: bool = False,
    debug: bool = False,
) -> CommandResponse:
    if hours <= 0:
        raise RuntimeError("--hours 必须大于 0")
    now = datetime.now().astimezone()
    orders = _dry_run_orders(now) if dry_run else _fetch_paid_orders(hours=hours, shop_name=shop_name, debug=debug)
    return CommandResponse(
        success=True,
        platform="jst",
        command="order pickup-watch",
        data={
            "hours": hours,
            "shop_name": shop_name or "",
            "checked_at": now.isoformat(timespec="seconds"),
            "dry_run": dry_run,
            "debug": debug,
            "orders": orders,
            "artifacts": [],
        },
    )
