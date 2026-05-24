from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from core.config_loader import get_path


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


def run_ops_json(args: list[str], *, interactive_recovery: bool | None = None) -> dict[str, Any]:
    json_args = args if "--json" in args else ["--json", *args]
    allow_interactive_recovery = (
        _default_interactive_recovery(json_args)
        if interactive_recovery is None
        else interactive_recovery and _default_interactive_recovery(json_args)
    )
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
            data = payload.get("data") or {}
            raise RuntimeError(
                f"Ops-Cli 执行失败 [{data.get('error_code', 'UNKNOWN')}]："
                f"{data.get('error', '未知错误')}；context={data.get('context_path', '')}"
            )
        raise RuntimeError("Ops-Cli 执行失败且响应结构不是对象")
    return payload
