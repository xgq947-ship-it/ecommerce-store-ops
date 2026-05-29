from __future__ import annotations

from core.runtime import send_notification


def test_dry_run_never_sends() -> None:
    calls: list = []
    result = send_notification("内容", dry_run=True, sender=lambda c, msgtype="text": calls.append(c))
    assert calls == []
    assert result["sent"] is False
    assert result["dry_run"] is True
    assert result["preview"] == "内容"


def test_empty_content_not_sent() -> None:
    calls: list = []
    result = send_notification("", dry_run=False, sender=lambda c, msgtype="text": calls.append(c))
    assert calls == []
    assert result["sent"] is False


def test_real_send_uses_sender_and_msgtype() -> None:
    calls: list = []

    def fake(content, msgtype="text"):
        calls.append((content, msgtype))
        return {"success": True, "sent": True}

    result = send_notification("告警", dry_run=False, msgtype="markdown", sender=fake)
    assert calls == [("告警", "markdown")]
    assert result["sent"] is True
