"""统一通知入口，供各 workflow 复用（提醒 / 失败告警）。

把「dry-run 只产预览、不发送；真实执行才推送」这条安全语义收敛到一处，避免每个 workflow
各写一遍。底层复用本机 `~/.hermes/scripts/send_wecom.py`（本地通知工具，非电商平台 API）。

约定返回结构：
- 无内容：{"success": True, "sent": False, "reason": "无通知内容"}
- dry-run：{"success": True, "sent": False, "dry_run": True, "preview": content}
- 真实发送：{"sent": True, **底层发送结果}
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

_HERMES_SCRIPTS = Path.home() / ".hermes" / "scripts"


def _load_send_wecom() -> Callable[..., Any]:
    if str(_HERMES_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_HERMES_SCRIPTS))
    from send_wecom import send_wecom  # noqa: E402

    return send_wecom


def send_notification(
    content: str,
    *,
    dry_run: bool,
    msgtype: str = "markdown",
    sender: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """发送通知；dry-run 下绝不真实推送，只返回预览。"""
    if not content:
        return {"success": True, "sent": False, "reason": "无通知内容"}
    if dry_run:
        return {"success": True, "sent": False, "dry_run": True, "preview": content}
    send = sender or _load_send_wecom()
    result = send(content, msgtype=msgtype)
    if isinstance(result, dict):
        return {"sent": True, **result}
    return {"success": True, "sent": True}
