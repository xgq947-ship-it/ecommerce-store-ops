from __future__ import annotations

import json
import os
import sys
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
    ) -> None:
        self.enabled = enabled
        self.base_url = base_url
        self.token = token
        self.receiver = receiver
        self.timeout = timeout
        self.agent_root = agent_root or Path(os.getenv("HERMES_AGENT_ROOT", Path.home() / ".hermes" / "hermes-agent"))
        self.env_path = env_path or Path(os.getenv("HERMES_ENV_PATH", Path.home() / ".hermes" / ".env"))

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
            sys.path.insert(0, str(self.agent_root))
            from tools.send_message_tool import send_message_tool

            raw = send_message_tool({"target": "weixin", "message": message})
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
