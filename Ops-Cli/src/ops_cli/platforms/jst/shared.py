from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ops_cli.capabilities import current_capability_execution


SceneCheckFn = Callable[[dict[str, Any]], dict[str, Any]]
SceneReadFn = Callable[[Path], dict[str, Any]]
SceneRefreshFn = Callable[..., Any]


def ensure_scene_file_ready(
    *,
    scene_path: Path,
    read_scene: SceneReadFn,
    validate_scene: SceneCheckFn,
    refresh_scene: SceneRefreshFn,
    next_command: str,
    missing_label: str,
    invalid_label: str,
) -> dict[str, Any]:
    initial_exists = scene_path.exists()
    if initial_exists:
        try:
            existing_check = validate_scene(read_scene(scene_path))
            if existing_check.get("valid"):
                return existing_check
        except Exception:
            pass

    execution = current_capability_execution()
    if execution is not None and not execution.allow_recovery:
        execution.recovery.mark_required()
        raise RuntimeError(f"{invalid_label} 不可用，当前执行模式禁止自动登录恢复。请先运行 `{next_command}`。")
    refresh_scene(force=initial_exists)

    if not scene_path.exists():
        raise RuntimeError(f"未找到{missing_label}：{scene_path}。请先运行 `{next_command}`。")

    refreshed_check = validate_scene(read_scene(scene_path))
    if not refreshed_check.get("valid"):
        reason = refreshed_check.get("reason") or "scene 不可用"
        raise RuntimeError(f"{invalid_label} 不可用：{reason}。请先运行 `{next_command}`。")
    if execution is not None:
        execution.recovery.mark_refreshed(scene_path.stem)
    return refreshed_check
