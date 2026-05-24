from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from core.config_loader import get_path


_AUTH_PLATFORMS = {"jst", "tmcs"}
_PREFLIGHTED_PLATFORMS: set[str] = set()


def ops_cli_root() -> Path:
    try:
        configured = get_path("ops_cli_root")
    except KeyError:
        configured = Path(__file__).resolve().parents[2].parent / "Ops-Cli"
    return Path(configured).expanduser().resolve()


def ops_cli_bin() -> Path:
    try:
        configured = get_path("ops_cli_bin")
    except KeyError:
        configured = ops_cli_root() / ".venv" / "bin" / "ops"
    return Path(configured).expanduser().resolve()


def _command_prefix() -> list[str]:
    root = ops_cli_root()
    if not root.is_dir():
        raise FileNotFoundError(f"Ops-Cli 项目路径不存在：{root}")
    binary = ops_cli_bin()
    if binary.exists():
        return [str(binary)]

    venv_python = root / ".venv" / "bin" / "python"
    if venv_python.exists():
        return [str(venv_python), "-m", "ops_cli.cli"]

    return [sys.executable, "-m", "ops_cli.cli"]


def _run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*_command_prefix(), *args],
        cwd=ops_cli_root(),
        text=True,
        capture_output=True,
        check=False,
    )


def _parse_payload(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if not stdout:
        raise RuntimeError("Ops-Cli 未返回 JSON 输出")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ops-Cli 返回非 JSON：{stdout[:500]}") from exc
    if isinstance(payload, dict):
        payload["_ops_stdout"] = stdout
        payload["_ops_stderr"] = stderr
    return payload


def _should_retry_interactively(payload: dict[str, Any], *, interactive_recovery: bool) -> bool:
    if not interactive_recovery or not sys.stdin.isatty():
        return False
    data = payload.get("data")
    if not isinstance(data, dict):
        return False
    return str(data.get("error_code") or "") == "AUTH_REQUIRED"


def _default_interactive_recovery(args: list[str]) -> bool:
    if "--dry-run" in args:
        return False
    return not ("auth" in args and "check" in args)


def _preflight_platform(args: list[str], *, allow_recovery: bool) -> str | None:
    if not allow_recovery or "--dry-run" in args:
        return None
    for index, part in enumerate(args):
        if part not in _AUTH_PLATFORMS:
            continue
        if index + 1 < len(args) and args[index + 1] == "auth":
            return None
        return part
    return None


def _raise_command_failure(payload: dict[str, Any], *, prefix: str = "Ops-Cli 执行失败") -> None:
    data = payload.get("data") or {}
    raise RuntimeError(
        f"{prefix} [{data.get('error_code', 'UNKNOWN')}]："
        f"{data.get('error', '未知错误')}；context={data.get('context_path', '')}"
    )


def preflight_platform_auth(platform: str) -> None:
    if platform not in _AUTH_PLATFORMS:
        raise ValueError(f"不支持认证预检的平台：{platform}")
    if platform in _PREFLIGHTED_PLATFORMS:
        return
    completed = _run_command(["--interactive-login", "--json", platform, "auth", "ensure"])
    payload = _parse_payload(completed)
    if completed.returncode != 0:
        _raise_command_failure(payload, prefix=f"{platform} 认证预检失败")
    _PREFLIGHTED_PLATFORMS.add(platform)


def run_ops_json(args: list[str], *, interactive_recovery: bool | None = None) -> dict[str, Any]:
    json_args = args if "--json" in args else ["--json", *args]
    allow_interactive_recovery = (
        _default_interactive_recovery(json_args)
        if interactive_recovery is None
        else interactive_recovery and _default_interactive_recovery(json_args)
    )
    platform = _preflight_platform(json_args, allow_recovery=allow_interactive_recovery)
    if platform is not None:
        preflight_platform_auth(platform)
    completed = _run_command(json_args)
    payload = _parse_payload(completed)
    if completed.returncode != 0 and isinstance(payload, dict) and _should_retry_interactively(
        payload,
        interactive_recovery=allow_interactive_recovery,
    ):
        completed = _run_command(["--interactive-login", *json_args])
        payload = _parse_payload(completed)
    if completed.returncode != 0:
        if isinstance(payload, dict):
            _raise_command_failure(payload)
        raise RuntimeError("Ops-Cli 执行失败且响应结构不是对象")
    return payload
