"""TMCS 物流履约数据概览读取。

读取路径（真实模式）：猫超首页 → 天机 → 商家仓履约 → 日常考核 → 数据概览。

本层只负责"读取原始数值"并输出统一 JSON：
- 考核指标 / 观测指标的原始值
- 平台返回的周数据预警等级（A/B/C 或 null）

指标是否合格、是否接近预警、是否要通知，全部交给业务层 workflow 判断，
本层不做任何阈值比较。

当前真实抓取尚未学习（需主浏览器学习页面 selector/接口后回灌 scene），
真实模式下 `_read_fulfillment_overview()` 抛 FULFILLMENT_OVERVIEW_NOT_FOUND；
dry-run 返回 simulated=True 的占位指标，供业务层联调与预警预览。
"""

from __future__ import annotations

from typing import Any

from ops_cli.output import CommandResponse
from ops_cli.platforms.tmcs.shared import (
    TMCS_FULFILLMENT_OVERVIEW_SCENE,
    TMCS_SITE,
)
from ops_cli.runtime_context import write_runtime_context


# 8 项指标键名（业务层据此判断），avg_pay_to_sign_hours 只记录、不预警。
METRIC_KEYS: tuple[str, ...] = (
    "pickup_24h_rate",
    "door_delivery_rate",
    "next_day_delivery_rate",
    "pickup_48h_rate",
    "seven_cp_rate",
    "avg_pay_to_sign_hours",
    "delivery_promise_rate",
    "exception_feedback_required",
)

# 数值型指标（dry-run 占位与真实解析都需为数字）。
_NUMERIC_METRIC_KEYS: tuple[str, ...] = (
    "pickup_24h_rate",
    "door_delivery_rate",
    "next_day_delivery_rate",
    "pickup_48h_rate",
    "seven_cp_rate",
    "avg_pay_to_sign_hours",
    "delivery_promise_rate",
)

# dry-run 占位：一组全部达标的模拟指标。
SIMULATED_METRICS: dict[str, Any] = {
    "pickup_24h_rate": 96.2,
    "door_delivery_rate": 78.5,
    "next_day_delivery_rate": 58.0,
    "pickup_48h_rate": 100.0,
    "seven_cp_rate": 100.0,
    "avg_pay_to_sign_hours": 36.5,
    "delivery_promise_rate": 93.1,
    "exception_feedback_required": False,
}


def parse_fulfillment_metrics(raw: Any) -> dict[str, Any]:
    """把页面读取到的原始结构归一成 8 项指标 dict。

    纯函数，不碰浏览器，便于单测。缺少必需数值指标时抛
    FULFILLMENT_OVERVIEW_NOT_FOUND。
    """
    if not isinstance(raw, dict):
        raise RuntimeError(
            "FULFILLMENT_OVERVIEW_NOT_FOUND：履约数据概览原始数据结构不是对象。"
        )

    metrics: dict[str, Any] = {}
    missing: list[str] = []
    for key in _NUMERIC_METRIC_KEYS:
        if key not in raw or raw[key] is None:
            missing.append(key)
            continue
        try:
            metrics[key] = round(float(raw[key]), 2)
        except (TypeError, ValueError):
            missing.append(key)

    if missing:
        raise RuntimeError(
            "FULFILLMENT_OVERVIEW_NOT_FOUND："
            f"履约数据概览缺少指标 {', '.join(missing)}。"
        )

    metrics["exception_feedback_required"] = bool(raw.get("exception_feedback_required", False))
    return metrics


def _read_fulfillment_overview() -> tuple[dict[str, Any], Any]:
    """真实读取履约数据概览（占位）。

    真实抓取需先在主浏览器学习页面（天机 → 商家仓履约 → 日常考核 → 数据概览）
    的 selector/接口结构并回灌 scene，再在此实现导航与提取。
    当前抛 FULFILLMENT_OVERVIEW_NOT_FOUND，避免乱猜选择器。
    """
    raise RuntimeError(
        "FULFILLMENT_OVERVIEW_NOT_FOUND：履约数据概览真实抓取尚未学习，"
        "请先运行 `ops --json tmcs fulfillment learn` 并在主浏览器完成页面学习。"
    )


def run_fulfillment_overview(*, dry_run: bool = False) -> CommandResponse:
    inputs = {"dry_run": dry_run}
    scene = f"{TMCS_SITE}/{TMCS_FULFILLMENT_OVERVIEW_SCENE}"

    if dry_run:
        metrics = dict(SIMULATED_METRICS)
        context_path = write_runtime_context(
            task_name="tmcs_fulfillment_overview",
            status="success",
            inputs=inputs,
            outputs={"simulated": True, "metrics": metrics},
        )
        return CommandResponse(
            success=True,
            platform="tmcs",
            command="fulfillment overview",
            data={
                "metrics": metrics,
                "weekly_warning_level": None,
                "source": "simulated",
                "simulated": True,
                "scene": scene,
                "dry_run": True,
                "artifacts": [],
                "context_path": str(context_path),
            },
        )

    raw, weekly_warning_level = _read_fulfillment_overview()
    metrics = parse_fulfillment_metrics(raw)
    context_path = write_runtime_context(
        task_name="tmcs_fulfillment_overview",
        status="success",
        inputs=inputs,
        outputs={"metrics": metrics, "weekly_warning_level": weekly_warning_level, "source": "page"},
    )
    return CommandResponse(
        success=True,
        platform="tmcs",
        command="fulfillment overview",
        data={
            "metrics": metrics,
            "weekly_warning_level": weekly_warning_level,
            "source": "page",
            "simulated": False,
            "scene": scene,
            "dry_run": False,
            "artifacts": [],
            "context_path": str(context_path),
        },
    )


def learn_fulfillment_overview(*, force: bool = False) -> CommandResponse:
    inputs = {"site": TMCS_SITE, "scene": TMCS_FULFILLMENT_OVERVIEW_SCENE, "force": force}
    note = (
        "履约数据概览读取尚未学习。请在主浏览器打开 天机 → 商家仓履约 → 日常考核 → 数据概览，"
        "完成页面学习并回灌 scene 后，再实现真实读取。"
    )
    context_path = write_runtime_context(
        task_name="tmcs_fulfillment_learn",
        status="success",
        inputs=inputs,
        outputs={"site": TMCS_SITE, "scene": TMCS_FULFILLMENT_OVERVIEW_SCENE, "note": note},
    )
    return CommandResponse(
        success=True,
        platform="tmcs",
        command="fulfillment learn",
        data={
            "site": TMCS_SITE,
            "scene": TMCS_FULFILLMENT_OVERVIEW_SCENE,
            "mode": "pending_learn",
            "note": note,
            "next_command": "ops --json tmcs fulfillment overview --dry-run",
            "context_path": str(context_path),
        },
    )
