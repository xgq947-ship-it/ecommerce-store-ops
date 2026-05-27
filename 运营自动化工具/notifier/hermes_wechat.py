from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class HermesWeChatNotifier:
    """Thin adapter over the verified local Hermes Weixin message tool."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        base_url: str | None = None,
        token: str | None = None,
        receiver: str | None = None,
        timeout: int = 10,
        agent_root: Path | None = None,
        env_path: Path | None = None,
        python_bin: Path | None = None,
    ) -> None:
        self.enabled = enabled
        self.base_url = base_url
        self.token = token
        self.receiver = receiver
        self.timeout = timeout
        self.agent_root = agent_root or Path(os.getenv("HERMES_AGENT_ROOT", Path.home() / ".hermes" / "hermes-agent"))
        self.env_path = env_path or Path(os.getenv("HERMES_ENV_PATH", Path.home() / ".hermes" / ".env"))
        configured_python = os.getenv("HERMES_PYTHON_BIN", "").strip()
        self.python_bin = python_bin or (Path(configured_python) if configured_python else self.agent_root / "venv" / "bin" / "python3")
        self.ops_scripts_dir = Path(__file__).resolve().parents[2] / "Ops-Cli" / "scripts"

    @classmethod
    def from_config(cls, config: dict[str, Any], *, force_enabled: bool = False) -> "HermesWeChatNotifier":
        enabled_value = os.getenv("HERMES_WECHAT_ENABLED", "")
        enabled = str(config.get("enabled", False)).lower() in {"1", "true", "yes", "on"}
        if enabled_value:
            enabled = enabled_value.lower() in {"1", "true", "yes", "on"}
        return cls(
            enabled=enabled or force_enabled,
            base_url=os.getenv("HERMES_WECHAT_BASE_URL") or None,
            token=os.getenv("HERMES_WECHAT_TOKEN") or None,
            receiver=os.getenv("HERMES_WECHAT_RECEIVER") or None,
            timeout=int(config.get("timeout_seconds", 10)),
        )

    def send_text(self, title: str, content: str, dry_run: bool = False) -> dict[str, Any]:
        message = f"{title}\n{content}".strip()
        if dry_run:
            return {"success": True, "sent": False, "dry_run": True, "preview": message}
        if not self.enabled:
            return {"success": True, "sent": False, "dry_run": False, "reason": "Hermes 微信通知未启用"}
        try:
            _load_env(self.env_path)
            if not self.agent_root.exists():
                raise RuntimeError(f"Hermes agent 目录不存在：{self.agent_root}")
            if not self.python_bin.exists():
                raise RuntimeError(f"Hermes Python 不存在：{self.python_bin}")
            if not self.ops_scripts_dir.exists():
                raise RuntimeError(f"Ops-Cli Hermes 发送脚本目录不存在：{self.ops_scripts_dir}")
            script = (
                "import json, sys\n"
                "sys.path.insert(0, sys.argv[1])\n"
                "from send_daily_profit_weixin import HERMES_ENV, _send_weixin_with_retry, load_env\n"
                "load_env(HERMES_ENV)\n"
                "message = sys.stdin.read()\n"
                "print(json.dumps(_send_weixin_with_retry(message), ensure_ascii=False))\n"
            )
            completed = subprocess.run(
                [str(self.python_bin), "-c", script, str(self.ops_scripts_dir)],
                cwd=str(self.agent_root),
                env=os.environ.copy(),
                input=message,
                text=True,
                capture_output=True,
                timeout=max(self.timeout, 45),
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(completed.stderr.strip() or "Hermes 消息发送命令执行失败")
            raw = completed.stdout.strip().splitlines()[-1]
            result = json.loads(raw)
            if not result.get("success"):
                raise RuntimeError(str(result.get("error") or raw))
            return {"success": True, "sent": True, "dry_run": False, "result": result}
        except Exception as exc:
            return {"success": False, "sent": False, "dry_run": False, "error": str(exc)}


def send_hermes_wechat_message(
    title: str,
    content: str,
    receiver: str | None = None,
    dry_run: bool = False,
) -> bool:
    notifier = HermesWeChatNotifier.from_config({}, force_enabled=not dry_run)
    notifier.receiver = receiver or notifier.receiver
    return bool(notifier.send_text(title, content, dry_run=dry_run).get("success"))
