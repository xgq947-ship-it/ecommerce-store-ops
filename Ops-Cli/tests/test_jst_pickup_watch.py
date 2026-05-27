from __future__ import annotations

from ops_cli.platforms.jst import pickup_watch


def test_has_pickup_record_matches_configured_trace_keyword() -> None:
    matched, keyword = pickup_watch.detect_pickup_record(
        [{"time": "2026-05-27 09:48:00", "content": "快件已由顺丰收取"}],
        ["已揽收", "快件已由顺丰收取"],
    )

    assert matched is True
    assert keyword == "快件已由顺丰收取"


def test_dry_run_produces_orders_for_risk_evaluation() -> None:
    response = pickup_watch.run_pickup_watch(hours=48, dry_run=True)

    assert response.success is True
    assert response.command == "order pickup-watch"
    assert response.data["dry_run"] is True
    assert len(response.data["orders"]) >= 9
    assert any(item["has_pickup_record"] for item in response.data["orders"])
    assert any("猫超" in item["platform"] for item in response.data["orders"])
    assert any(item["logistics_no"] and not item["logistics_traces"] for item in response.data["orders"])
