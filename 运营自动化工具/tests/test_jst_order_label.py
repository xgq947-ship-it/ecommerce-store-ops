from __future__ import annotations

import json
import sys

from tasks.jst_order_label import main as order_label


def test_dry_run_does_not_enable_interactive_recovery(monkeypatch, capsys) -> None:
    observed: dict[str, object] = {}

    def fake_run_ops_json(args, **kwargs):
        observed["args"] = args
        observed["kwargs"] = kwargs
        return {"success": True, "data": {}}

    monkeypatch.setattr(order_label, "run_ops_json", fake_run_ops_json)
    monkeypatch.setattr(sys, "argv", ["jst_order_label", "--dry-run", "--order-id", "ORDER001"])

    assert order_label.main() == 0
    assert json.loads(capsys.readouterr().out)["dry_run"] is True
    assert observed["kwargs"] == {"interactive_recovery": False}


def test_real_run_enables_interactive_recovery(monkeypatch, capsys) -> None:
    observed: dict[str, object] = {}

    def fake_run_ops_json(args, **kwargs):
        observed["args"] = args
        observed["kwargs"] = kwargs
        return {"success": True, "data": {}}

    monkeypatch.setattr(order_label, "run_ops_json", fake_run_ops_json)
    monkeypatch.setattr(sys, "argv", ["jst_order_label", "--order-id", "ORDER001"])

    assert order_label.main() == 0
    assert json.loads(capsys.readouterr().out)["dry_run"] is False
    assert observed["kwargs"] == {"interactive_recovery": True}
