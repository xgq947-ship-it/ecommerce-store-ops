from __future__ import annotations

import sys

from tasks import append_brush_orders


def test_real_append_preflights_jst_before_input_copy_or_workbook_writes(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        append_brush_orders,
        "preflight_platform_auth",
        lambda platform: calls.append(f"preflight:{platform}"),
        raising=False,
    )
    monkeypatch.setattr(append_brush_orders, "has_xlsx_files", lambda path: False)
    monkeypatch.setattr(
        append_brush_orders,
        "copy_wechat_source_files",
        lambda month, day, print_skipped=False: calls.append("copy") or [],
    )
    monkeypatch.setattr(append_brush_orders, "read_all_source_batches", lambda: [])
    monkeypatch.setattr(append_brush_orders, "write_latest_brush_orders", lambda orders: calls.append("latest"))
    monkeypatch.setattr(append_brush_orders, "clear_source_dir", lambda: calls.append("clear"))

    append_brush_orders.run(dry_run=False)

    assert calls[0] == "preflight:jst"
    assert calls == ["preflight:jst", "copy", "latest", "clear"]


def test_dry_run_append_does_not_preflight_jst(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        append_brush_orders,
        "preflight_platform_auth",
        lambda platform: calls.append(f"preflight:{platform}"),
        raising=False,
    )
    monkeypatch.setattr(append_brush_orders, "has_xlsx_files", lambda path: True)
    monkeypatch.setattr(append_brush_orders, "read_all_source_batches", lambda: [])

    append_brush_orders.run(dry_run=True)

    assert calls == []


def test_main_routes_to_workflow_without_direct_append(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(sys, "argv", ["append_brush_orders", "--dry-run", "昨天的"])
    monkeypatch.setattr(append_brush_orders, "_run_workflow", lambda args: calls.append(list(args)) or 0, raising=False)
    monkeypatch.setattr(
        append_brush_orders,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("旧入口不应直接追加登记表")),
    )

    assert append_brush_orders.main() == 0
    assert calls == [["append_brush_orders", "--dry-run", "昨天的"]]
