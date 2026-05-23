from __future__ import annotations

from ops_cli.capabilities import capability_ids, get_capability


def test_registry_includes_existing_platform_capabilities() -> None:
    registered = capability_ids()

    assert "browser.check" in registered
    assert "tmcs.bill.download" in registered
    assert "tmcs.promotion-bill.download" in registered
    assert "tmcs.inventory.export" in registered
    assert "jst.order.invoice" in registered
    assert "jst.order.reimburse" in registered
    assert "jst.profit.month" in registered


def test_bill_capability_declares_scene_and_execution_contract() -> None:
    spec = get_capability("tmcs.bill.download")

    assert spec.platform == "tmcs"
    assert spec.command == "bill download"
    assert spec.recovery_policy == "interactive_if_tty"
    assert spec.dry_run_policy == "check_only"
    assert spec.artifact_types == ("xlsx",)
    assert "statement_bill_list_for_supplier" in spec.scenes
    assert "statement_bill_dynamic_list" in spec.scenes


def test_registry_uses_existing_scene_names_for_recovery_hints() -> None:
    assert "order_logistics_trace" in get_capability("jst.order.logistics").scenes
    assert "profit_multi_dimension_report" in get_capability("jst.order.stats").scenes
    assert "tmcs_promotion_zdx_bill_export" in get_capability("tmcs.promotion-bill.download").scenes
