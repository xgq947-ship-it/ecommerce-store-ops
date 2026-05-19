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


def run_ops_json(args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        [*_command_prefix(), *args],
        cwd=ops_cli_root(),
        text=True,
        capture_output=True,
        check=False,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if completed.returncode != 0:
        raise RuntimeError(stderr or stdout or "Ops-Cli 执行失败")
    if not stdout:
        raise RuntimeError("Ops-Cli 未返回输出")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ops-Cli 返回非 JSON：{stdout[:500]}") from exc
    if isinstance(payload, dict):
        payload["_ops_stdout"] = stdout
        payload["_ops_stderr"] = stderr
    return payload
