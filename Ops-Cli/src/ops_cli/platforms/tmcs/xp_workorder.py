"""TMCS XP 工单数量读取与 scene 学习。

只暴露两条 capability：
- count：读取当前 XP 工单数量，可与阈值比较
- learn：在主浏览器辅助下捕获 scene

工单接口 endpoint / 字段名在 learn 阶段从主浏览器抓取的 scene 中获取，
本模块不写死任何业务 URL；count 通过 scene 回放工单列表/计数接口拿到总数。

dry-run：完全跳过 scene 读取与平台请求，返回 simulated=True 的占位结果。
"""

from __future__ import annotations

from typing import Any

from ops_cli.capabilities import (
    current_capability_execution,
    mark_scene_refreshed,
    require_interactive_recovery,
)
from ops_cli.integrations.sessionhub import (
    SessionHubIntegrationError,
    get_scene_manager,
)
from ops_cli.output import CommandResponse
from ops_cli.platforms.tmcs.shared import (
    TMCS_SITE,
    TMCS_XP_WORKORDER_COUNT_SCENE,
    check_scene_or_fail,
    is_probable_auth_error,
    load_scene_or_fail,
    sanitize_replay_headers,
    tmcs_request,
)
from ops_cli.runtime_context import write_runtime_context


DEFAULT_THRESHOLD = 4
_NEXT_COMMAND = "ops --json tmcs xp-workorder learn"

# 可能承载工单数量的字段候选，按命中优先级排列。
_COUNT_FIELD_CANDIDATES = (
    "totalCount",
    "total_count",
    "total",
    "count",
    "unprocessedCount",
    "pendingCount",
    "waitHandleCount",
    "todoCount",
    "unhandledCount",
)


def _iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _iter_dicts(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_dicts(item)


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value:  # NaN
            return None
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            try:
                return int(float(text))
            except ValueError:
                return None
    return None


def extract_workorder_count(payload: Any) -> int | None:
    """从平台返回的任意 JSON 中提取工单数量。"""
    if payload is None:
        return None
    # 优先看顶层与典型容器
    seeds: list[Any] = [payload]
    if isinstance(payload, dict):
        for key in ("data", "result", "model"):
            nested = payload.get(key)
            if nested is not None:
                seeds.append(nested)
    for seed in seeds:
        for row in _iter_dicts(seed):
            for field in _COUNT_FIELD_CANDIDATES:
                if field in row:
                    parsed = _coerce_int(row[field])
                    if parsed is not None and parsed >= 0:
                        return parsed
    # 兜底：列表长度
    for seed in seeds:
        if isinstance(seed, dict):
            for key in ("rows", "items", "list", "records", "datas"):
                if isinstance(seed.get(key), list):
                    return len(seed[key])
    return None


def _request_workorder_count(scene: dict[str, Any]) -> int:
    method = str(scene.get("method") or "GET").upper()
    url = scene.get("url")
    if not url:
        raise RuntimeError(f"scene {TMCS_XP_WORKORDER_COUNT_SCENE} 缺少 url")
    headers = sanitize_replay_headers(scene.get("headers") or {}, scene.get("cookies"))
    post_json = scene.get("post_data_json")
    post_data = scene.get("post_data") if post_json is None else None
    if isinstance(post_data, str):
        body_bytes: Any = post_data.encode("utf-8")
    else:
        body_bytes = None
    _, parsed, _ = tmcs_request(
        method,
        str(url),
        headers=headers,
        json_body=post_json,
        data_body=body_bytes,
    )
    count = extract_workorder_count(parsed)
    if count is None:
        raise RuntimeError(
            "WORKORDER_COUNT_NOT_FOUND：scene 接口返回中未识别到工单数量字段；"
            "请重新运行 `ops --json tmcs xp-workorder learn --force` 更新 scene。"
        )
    return count


def count_xp_workorders(
    *,
    threshold: int = DEFAULT_THRESHOLD,
    dry_run: bool = False,
) -> CommandResponse:
    inputs = {"threshold": threshold, "dry_run": dry_run}

    if dry_run:
        context_path = write_runtime_context(
            task_name="tmcs_xp_workorder_count",
            status="success",
            inputs=inputs,
            outputs={"simulated": True, "count": 0, "threshold": threshold},
        )
        return CommandResponse(
            success=True,
            platform="tmcs",
            command="xp-workorder count",
            data={
                "count": 0,
                "threshold": threshold,
                "exceeded": False,
                "source": "simulated",
                "simulated": True,
                "scene": f"{TMCS_SITE}/{TMCS_XP_WORKORDER_COUNT_SCENE}",
                "dry_run": True,
                "context_path": str(context_path),
            },
        )

    retried_for_auth = False
    while True:
        scene = load_scene_or_fail(
            TMCS_SITE, TMCS_XP_WORKORDER_COUNT_SCENE, next_command=_NEXT_COMMAND
        )
        check_scene_or_fail(
            TMCS_SITE, TMCS_XP_WORKORDER_COUNT_SCENE, next_command=_NEXT_COMMAND
        )
        try:
            count = _request_workorder_count(scene)
            break
        except RuntimeError as exc:
            if retried_for_auth or not is_probable_auth_error(exc):
                raise
            require_interactive_recovery(TMCS_XP_WORKORDER_COUNT_SCENE)
            learn_xp_workorder_count(force=True)
            mark_scene_refreshed(TMCS_XP_WORKORDER_COUNT_SCENE)
            retried_for_auth = True

    exceeded = count > threshold
    context_path = write_runtime_context(
        task_name="tmcs_xp_workorder_count",
        status="success",
        inputs=inputs,
        outputs={"count": count, "threshold": threshold, "exceeded": exceeded},
    )
    return CommandResponse(
        success=True,
        platform="tmcs",
        command="xp-workorder count",
        data={
            "count": count,
            "threshold": threshold,
            "exceeded": exceeded,
            "source": "api",
            "simulated": False,
            "scene": f"{TMCS_SITE}/{TMCS_XP_WORKORDER_COUNT_SCENE}",
            "dry_run": False,
            "context_path": str(context_path),
        },
    )


def learn_xp_workorder_count(*, force: bool = False) -> CommandResponse:
    inputs = {
        "site": TMCS_SITE,
        "scene": TMCS_XP_WORKORDER_COUNT_SCENE,
        "force": force,
    }
    manager = get_scene_manager()
    execution = current_capability_execution()
    if execution is not None and not execution.allow_recovery:
        execution.recovery.mark_required()
        raise RuntimeError(
            f"scene {TMCS_XP_WORKORDER_COUNT_SCENE} 需要交互登录捕获，"
            "请在交互终端运行：ops --json --interactive-login tmcs xp-workorder learn"
        )
    try:
        if force:
            manager.capture_scene(TMCS_SITE, TMCS_XP_WORKORDER_COUNT_SCENE)
        else:
            manager.ensure_scene(TMCS_SITE, TMCS_XP_WORKORDER_COUNT_SCENE)
    except SessionHubIntegrationError as exc:
        raise RuntimeError(f"SCENE_CAPTURE_FAILED：{exc}") from exc
    check = manager.check_scene(TMCS_SITE, TMCS_XP_WORKORDER_COUNT_SCENE)
    if check.get("status") != "valid":
        reason = (check.get("check_result") or {}).get("reason") or "scene 不可用"
        raise RuntimeError(f"SCENE_CAPTURE_FAILED：{reason}")
    mark_scene_refreshed(TMCS_XP_WORKORDER_COUNT_SCENE)
    context_path = write_runtime_context(
        task_name="tmcs_xp_workorder_learn",
        status="success",
        inputs=inputs,
        outputs={"site": TMCS_SITE, "scene": TMCS_XP_WORKORDER_COUNT_SCENE},
    )
    return CommandResponse(
        success=True,
        platform="tmcs",
        command="xp-workorder learn",
        data={
            "site": TMCS_SITE,
            "scene": TMCS_XP_WORKORDER_COUNT_SCENE,
            "next_command": "ops --json tmcs xp-workorder count",
            "context_path": str(context_path),
        },
    )
