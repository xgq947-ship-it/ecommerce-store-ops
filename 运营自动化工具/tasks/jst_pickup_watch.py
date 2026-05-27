#!/usr/bin/env python3
"""Business risk evaluation and alerting for JST pickup monitoring."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import traceback
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clients.ops_cli_client import run_ops_json  # noqa: E402
from core.config_loader import get_path  # noqa: E402
from notifier.hermes_wechat import HermesWeChatNotifier  # noqa: E402


REPORT_HEADERS = [
    ("shop_name", "店铺名"),
    ("platform", "平台来源"),
    ("platform_order_no", "平台订单号"),
    ("jst_order_no", "聚水潭订单号"),
    ("jst_pay_time", "聚水潭付款时间"),
    ("maochao_real_pay_time", "猫超真实付款时间"),
    ("effective_pay_time", "修正后付款时间"),
    ("pay_time_source", "付款时间来源"),
    ("pay_time_offset_minutes", "付款时间修正分钟数"),
    ("check_time", "当前检查时间"),
    ("risk_hours", "距离修正后付款小时数"),
    ("logistics_company", "快递公司"),
    ("logistics_no", "物流单号"),
    ("latest_logistics_status", "当前物流状态"),
    ("has_pickup_record", "是否已有揽收记录"),
    ("pickup_matched_keyword", "命中的揽收关键词"),
    ("risk_level", "风险等级"),
    ("after_1730_order", "是否 17:30 后付款订单"),
    ("handling_advice", "处理建议"),
]

ADVICE = {
    "普通提醒": "请关注该订单物流揽收情况，避免超过 24 小时未揽收。",
    "高危提醒": "该订单距离 24 小时揽收风险较近，请优先联系仓库或快递确认。",
    "已超时": "该订单已超过 24 小时未识别到揽收记录，请立即处理并登记异常原因。",
    "正常": "",
}


def load_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or get_path("pickup_watch_config")
    if not Path(config_path).is_absolute():
        config_path = ROOT / config_path
    return json.loads(Path(config_path).read_text(encoding="utf-8"))


def _parse_datetime(value: str, now: datetime) -> datetime:
    parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=now.tzinfo)


def _is_maochao(order: dict[str, Any]) -> bool:
    values = " ".join(str(order.get(key) or "") for key in ("platform", "order_source", "shop_name")).lower()
    return any(token in values for token in ("猫超", "天猫超市", "cat_supermarket", "tmcs"))


def evaluate_order(order: dict[str, Any], config: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    rule = config["platform_rules"]["cat_supermarket"]
    jst_pay_time = _parse_datetime(str(order["jst_pay_time"]), now)
    real_pay_value = str(order.get("maochao_real_pay_time") or "").strip()
    offset_minutes = 0
    if real_pay_value and _is_maochao(order):
        effective_pay_time = _parse_datetime(real_pay_value, now)
        pay_time_source = "maochao_real_pay_time"
    elif rule.get("enabled", True) and _is_maochao(order):
        offset_minutes = int(rule["pay_time_offset_minutes"])
        effective_pay_time = jst_pay_time - timedelta(minutes=offset_minutes)
        pay_time_source = "jst_pay_time_adjusted"
    else:
        effective_pay_time = jst_pay_time
        pay_time_source = "jst_pay_time"

    risk_hours = round((now - effective_pay_time).total_seconds() / 3600, 2)
    stop_time = time.fromisoformat(config["pickup_watch"]["warehouse"]["stop_shipping_time"])
    after_stop = effective_pay_time.time() >= stop_time
    suppress = bool(
        rule.get("after_1730_orders_next_day", True)
        and after_stop
        and effective_pay_time.date() == now.date()
    )
    thresholds = config["pickup_watch"]["risk_thresholds"]
    if order.get("has_pickup_record") or suppress:
        risk_level = "正常"
    elif risk_hours >= float(thresholds["timeout_hours"]):
        risk_level = "已超时"
    elif risk_hours >= float(thresholds["high_risk_hours"]):
        risk_level = "高危提醒"
    elif risk_hours >= float(thresholds["normal_reminder_hours"]):
        risk_level = "普通提醒"
    else:
        risk_level = "正常"

    return {
        **order,
        "effective_pay_time": effective_pay_time.isoformat(timespec="seconds"),
        "pay_time_source": pay_time_source,
        "pay_time_offset_minutes": offset_minutes,
        "check_time": now.isoformat(timespec="seconds"),
        "risk_hours": risk_hours,
        "risk_level": risk_level,
        "after_1730_order": after_stop,
        "suppressed_until_next_day": suppress,
        "handling_advice": ADVICE[risk_level],
    }


def evaluate_orders(orders: list[dict[str, Any]], config: dict[str, Any], *, now: datetime) -> tuple[list[dict[str, Any]], dict[str, int]]:
    evaluated = [evaluate_order(order, config, now=now) for order in orders]
    abnormal = [item for item in evaluated if not item.get("has_pickup_record") and item["risk_level"] != "正常"]
    abnormal.sort(key=lambda item: float(item["risk_hours"]), reverse=True)
    counts = {
        "checked_orders": len(evaluated),
        "abnormal_orders": len(abnormal),
        "normal_reminder": sum(item["risk_level"] == "普通提醒" for item in abnormal),
        "high_risk": sum(item["risk_level"] == "高危提醒" for item in abnormal),
        "timed_out": sum(item["risk_level"] == "已超时" for item in abnormal),
        "suppressed_after_1730": sum(bool(item["suppressed_until_next_day"]) for item in evaluated),
    }
    return abnormal, counts


def write_reports(rows: list[dict[str, Any]], output_dir: Path, *, timestamp: str) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"聚水潭揽收监控_{timestamp}.csv"
    xlsx_path = output_dir / f"聚水潭揽收监控_{timestamp}.xlsx"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([label for _, label in REPORT_HEADERS])
        for row in rows:
            writer.writerow([row.get(key, "") for key, _ in REPORT_HEADERS])
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "揽收异常订单"
    sheet.append([label for _, label in REPORT_HEADERS])
    for row in rows:
        sheet.append([row.get(key, "") for key, _ in REPORT_HEADERS])
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    workbook.save(xlsx_path)
    return {"csv_path": str(csv_path.resolve()), "xlsx_path": str(xlsx_path.resolve())}


def build_notification_content(*, checked_at: str, hours: int, counts: dict[str, int], rows: list[dict[str, Any]], xlsx_path: str) -> str:
    lines = [
        f"当前检查时间：{checked_at}",
        f"检查订单范围：近 {hours} 小时",
        f"普通提醒订单数量：{counts['normal_reminder']}",
        f"高危提醒订单数量：{counts['high_risk']}",
        f"已超时订单数量：{counts['timed_out']}",
        "",
        "TOP 10 高风险订单：",
    ]
    for item in rows[:10]:
        lines.append(
            f"{item.get('shop_name', '')} | {item.get('platform_order_no', '')} | "
            f"{item['risk_hours']}h | {item['risk_level']} | {item.get('logistics_company', '')} | "
            f"{item.get('logistics_no', '')} | {item.get('latest_logistics_status', '')}"
        )
    if not rows:
        lines.append("无异常订单")
    lines.extend(["", f"异常订单文件：{xlsx_path}"])
    return "\n".join(lines)[:3500]


def _setup_logger(timestamp: str) -> tuple[logging.Logger, Path]:
    log_dir = get_path("logs_dir")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"jst_pickup_watch_{timestamp}.log"
    logger = logging.getLogger(f"jst_pickup_watch.{timestamp}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(logging.FileHandler(log_path, encoding="utf-8"))
    return logger, log_path.resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="聚水潭订单揽收监控")
    parser.add_argument("--dry-run", action="store_true", help="使用模拟订单，不请求真实聚水潭、不发送微信")
    parser.add_argument("--hours", type=int, default=None, help="检查最近付款订单小时数")
    parser.add_argument("--debug", action="store_true", help="透传 Ops-Cli 调试参数")
    parser.add_argument("--notify", action="store_true", help="通过 Hermes 微信推送检查结果")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    hours = args.hours or int(config["pickup_watch"]["hours"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger, log_path = _setup_logger(timestamp)
    logger.info("聚水潭揽收监控开始 hours=%s dry_run=%s notify=%s", hours, args.dry_run, args.notify)
    try:
        command = ["--json", "jst", "order", "pickup-watch", "--hours", str(hours), "--output", "json"]
        if args.dry_run:
            command.append("--dry-run")
        if args.debug:
            command.append("--debug")
        payload = run_ops_json(command, interactive_recovery=not args.dry_run)
        data = payload["data"]
        checked_at = str(data.get("checked_at") or datetime.now().astimezone().isoformat(timespec="seconds"))
        check_time = _parse_datetime(checked_at, datetime.now().astimezone())
        abnormal, counts = evaluate_orders(list(data.get("orders") or []), config, now=check_time)
        output_dir = get_path("pickup_watch_reports_dir")
        if not output_dir.is_absolute():
            output_dir = ROOT / output_dir
        artifacts = write_reports(abnormal, output_dir, timestamp=timestamp)
        content = build_notification_content(
            checked_at=checked_at,
            hours=hours,
            counts=counts,
            rows=abnormal,
            xlsx_path=artifacts["xlsx_path"],
        )
        notifier_config = config.get("notifier", {}).get("hermes_wechat", {})
        notifier = HermesWeChatNotifier.from_config(notifier_config, force_enabled=args.notify)
        should_notify = args.dry_run or args.notify or notifier.enabled
        notification = notifier.send_text("聚水潭订单揽收异常提醒", content, dry_run=args.dry_run) if should_notify else {
            "success": True,
            "sent": False,
            "reason": "Hermes 微信通知未启用",
        }
        logger.info("拉取订单数量=%s 异常订单数量=%s counts=%s", counts["checked_orders"], counts["abnormal_orders"], counts)
        logger.info("报告文件=%s", artifacts)
        logger.info("Hermes 微信推送结果=%s", notification)
        result = {
            "success": True,
            "task": "jst_pickup_watch",
            "dry_run": args.dry_run,
            "hours": hours,
            "checked_at": checked_at,
            "summary": counts,
            "reports": artifacts,
            "task_log_path": str(log_path),
            "notification": notification,
            "ops_result": {key: value for key, value in payload.items() if not key.startswith("_ops_")},
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        logger.error("执行失败：%s\n%s", exc, traceback.format_exc())
        print(json.dumps({"success": False, "task": "jst_pickup_watch", "error": str(exc), "task_log_path": str(log_path)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
