from __future__ import annotations

import pytest

from ops_cli.capabilities import capability_ids, get_capability
from ops_cli.cli import app  # noqa: F401
from ops_cli.platforms.tmcs import fulfillment


def test_fulfillment_capability_registered() -> None:
    registered = capability_ids()
    assert "tmcs.fulfillment.overview" in registered
    assert "tmcs.fulfillment.learn" in registered

    spec = get_capability("tmcs.fulfillment.overview")
    assert spec.platform == "tmcs"
    assert spec.command == "fulfillment overview"
    assert "fulfillment_overview" in spec.scenes


def test_dry_run_returns_simulated(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)

    response = fulfillment.run_fulfillment_overview(dry_run=True)

    assert response.success is True
    assert response.platform == "tmcs"
    assert response.command == "fulfillment overview"
    data = response.data
    assert data["simulated"] is True
    assert data["source"] == "simulated"
    assert data["dry_run"] is True
    assert data["weekly_warning_level"] is None
    assert data["scene"].endswith("/fulfillment_overview")
    assert data["context_path"].endswith(".json")
    metrics = data["metrics"]
    for key in fulfillment.METRIC_KEYS:
        assert key in metrics
    assert metrics["pickup_24h_rate"] == 96.2
    assert metrics["exception_feedback_required"] is False


def test_parse_metrics_normalizes() -> None:
    raw = {
        "pickup_24h_rate": "96.25",
        "door_delivery_rate": 78.5,
        "next_day_delivery_rate": 58,
        "pickup_48h_rate": 100,
        "seven_cp_rate": 100,
        "avg_pay_to_sign_hours": "36.5",
        "delivery_promise_rate": 93.1,
        "exception_feedback_required": 1,
    }
    metrics = fulfillment.parse_fulfillment_metrics(raw)
    assert metrics["pickup_24h_rate"] == 96.25
    assert metrics["next_day_delivery_rate"] == 58.0
    assert metrics["exception_feedback_required"] is True


def test_parse_metrics_missing_raises_not_found() -> None:
    with pytest.raises(RuntimeError, match="FULFILLMENT_OVERVIEW_NOT_FOUND"):
        fulfillment.parse_fulfillment_metrics({"pickup_24h_rate": 96.2})


def test_real_read_raises_not_found(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)

    with pytest.raises(RuntimeError, match="FULFILLMENT_OVERVIEW_NOT_FOUND"):
        fulfillment.run_fulfillment_overview(dry_run=False)


def test_learn_returns_pending_note(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)

    response = fulfillment.learn_fulfillment_overview()
    assert response.success is True
    assert response.data["mode"] == "pending_learn"
    assert response.data["scene"] == "fulfillment_overview"
