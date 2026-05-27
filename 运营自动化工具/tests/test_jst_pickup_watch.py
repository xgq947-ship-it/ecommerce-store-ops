from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse
import json
import logging
import subprocess

from tasks import jst_pickup_watch
from notifier.hermes_wechat import HermesWeChatNotifier


def config() -> dict:
    return {
        "pickup_watch": {
            "hours": 48,
            "risk_thresholds": {
                "normal_reminder_hours": 12,
                "high_risk_hours": 20,
                "timeout_hours": 24,
            },
            "warehouse": {"stop_shipping_time": "17:30"},
        },
        "platform_rules": {
            "cat_supermarket": {
                "enabled": True,
                "pay_time_offset_minutes": 30,
                "after_1730_orders_next_day": True,
            }
        },
    }


def test_maochao_order_uses_adjusted_effective_pay_time() -> None:
    order = {
        "platform": "天猫超市",
        "jst_pay_time": "2026-05-26T22:30:00+08:00",
        "has_pickup_record": False,
    }

    evaluated = jst_pickup_watch.evaluate_order(
        order,
        config(),
        now=datetime.fromisoformat("2026-05-27T18:00:00+08:00"),
    )

    assert evaluated["effective_pay_time"] == "2026-05-26T22:00:00+08:00"
    assert evaluated["pay_time_source"] == "jst_pay_time_adjusted"
    assert evaluated["pay_time_offset_minutes"] == 30
    assert evaluated["risk_level"] == "高危提醒"


def test_real_maochao_pay_time_wins_over_adjustment() -> None:
    order = {
        "platform": "猫超",
        "jst_pay_time": "2026-05-26T22:30:00+08:00",
        "maochao_real_pay_time": "2026-05-26T21:55:00+08:00",
        "has_pickup_record": False,
    }

    evaluated = jst_pickup_watch.evaluate_order(
        order,
        config(),
        now=datetime.fromisoformat("2026-05-27T18:00:00+08:00"),
    )

    assert evaluated["effective_pay_time"] == "2026-05-26T21:55:00+08:00"
    assert evaluated["pay_time_source"] == "maochao_real_pay_time"
    assert evaluated["risk_level"] == "高危提醒"


def test_after_1730_effective_pay_time_is_not_alerted_on_same_evening() -> None:
    order = {
        "platform": "其他平台",
        "jst_pay_time": "2026-05-27T17:31:00+08:00",
        "has_pickup_record": False,
    }

    evaluated = jst_pickup_watch.evaluate_order(
        order,
        config(),
        now=datetime.fromisoformat("2026-05-27T18:00:00+08:00"),
    )

    assert evaluated["after_1730_order"] is True
    assert evaluated["suppressed_until_next_day"] is True
    assert evaluated["risk_level"] == "正常"


def test_notification_only_lists_abnormal_platform_order_numbers() -> None:
    rows = [
        {
            "platform_order_no": "P-TIMEOUT",
            "risk_level": "已超时",
        },
        {
            "platform_order_no": "P-HIGH",
            "risk_level": "高危提醒",
        },
        {
            "platform_order_no": "P-REMIND",
            "risk_level": "普通提醒",
        },
    ]

    content = jst_pickup_watch.build_notification_content(
        counts={"abnormal_orders": 3, "normal_reminder": 1, "high_risk": 1, "timed_out": 1},
        rows=rows,
    )

    assert content == "异常订单 3 单\n已超时：P-TIMEOUT\n高危：P-HIGH\n提醒：P-REMIND"
    assert not hasattr(jst_pickup_watch, "write_reports")


def test_hermes_dry_run_returns_preview_without_sending() -> None:
    notifier = HermesWeChatNotifier(enabled=True)

    result = notifier.send_text("聚水潭订单揽收异常提醒", "模拟消息", dry_run=True)

    assert result["success"] is True
    assert result["dry_run"] is True
    assert "模拟消息" in result["preview"]


def test_hermes_real_send_runs_in_agent_python(monkeypatch, tmp_path: Path) -> None:
    agent_root = tmp_path / "hermes-agent"
    python_bin = agent_root / "venv" / "bin" / "python3"
    python_bin.parent.mkdir(parents=True)
    python_bin.write_text("", encoding="utf-8")
    called: dict[str, object] = {}
    notifier = HermesWeChatNotifier(enabled=True, agent_root=agent_root, env_path=tmp_path / ".env")
    notifier.ops_scripts_dir = tmp_path / "ops-scripts"
    notifier.ops_scripts_dir.mkdir()

    def fake_run(command, **kwargs):
        called["command"] = command
        called["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, stdout='{"success": true}', stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = notifier.send_text("聚水潭订单揽收异常提醒", "正式消息")

    assert result["success"] is True
    assert result["sent"] is True
    assert called["command"][0] == str(python_bin)
    assert called["command"][3] == str(notifier.ops_scripts_dir)
    assert called["kwargs"]["input"] == "聚水潭订单揽收异常提醒\n正式消息"
    assert called["kwargs"]["timeout"] == 45


def test_no_abnormal_orders_does_not_send_notification(monkeypatch, tmp_path: Path, capsys) -> None:
    send_calls: list[tuple[str, str, bool]] = []

    class FakeNotifier:
        enabled = True

        def send_text(self, title: str, content: str, dry_run: bool = False) -> dict:
            send_calls.append((title, content, dry_run))
            return {"success": True, "sent": True}

    monkeypatch.setattr(
        jst_pickup_watch,
        "parse_args",
        lambda: argparse.Namespace(dry_run=False, hours=48, debug=False, notify=True),
    )
    monkeypatch.setattr(jst_pickup_watch, "load_config", config)
    monkeypatch.setattr(
        jst_pickup_watch,
        "_setup_logger",
        lambda timestamp: (logging.getLogger("pickup-watch-test"), tmp_path / "task.log"),
    )
    monkeypatch.setattr(
        jst_pickup_watch,
        "run_ops_json",
        lambda command, interactive_recovery: {
            "success": True,
            "data": {"checked_at": "2026-05-28T10:00:00+08:00", "orders": []},
        },
    )
    monkeypatch.setattr(
        jst_pickup_watch.HermesWeChatNotifier,
        "from_config",
        lambda *args, **kwargs: FakeNotifier(),
    )

    assert jst_pickup_watch.main() == 0
    result = json.loads(capsys.readouterr().out)

    assert send_calls == []
    assert result["notification"] == {
        "success": True,
        "sent": False,
        "reason": "无异常订单，不发送微信",
    }
