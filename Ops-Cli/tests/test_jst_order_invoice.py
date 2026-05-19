from decimal import Decimal
from pathlib import Path

from ops_cli.platforms.jst import invoice


def test_build_invoice_payload_defaults() -> None:
    payload = invoice.build_invoice_workorder_payload(
        order_id="TB123",
        internal_order_id="10001",
        online_order_id="LP10001",
        invoice_type="专用发票",
        title="YOUR_ACCOUNT",
        tax_no="91330000TEST",
        address="YOUR_ACCOUNT",
        phone="YOUR_ACCOUNT",
        bank="YOUR_ACCOUNT",
        bank_account="YOUR_ACCOUNT",
        amount=Decimal("128.50"),
        quantity=1,
    )

    data = payload["data"]
    assert data["title"] == "发票"
    assert data["orderIds"] == ["10001"]
    assert {"fieldId": "invoiceTypeField", "value": "专用发票"} in data["businessField"]
    assert {"fieldId": "invoiceAmountField", "value": 128.5} in data["businessField"]
    assert {"fieldId": "invoiceQuantityField", "value": 1} in data["businessField"]


def test_run_invoice_workorder_dry_run_writes_context(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    def fake_resolve_order_identity(order_id: str, outer_order_id: str | None = None) -> dict[str, str]:
        return {"order_id": order_id, "internal_order_id": "10001", "online_order_id": "LP10001", "matched_filter": "outer_so_id"}

    monkeypatch.setattr(invoice, "_resolve_order_identity", fake_resolve_order_identity)

    response = invoice.run_order_invoice_workorder(
        order_id="TB123",
        outer_order_id=None,
        invoice_type="专用发票",
        title="YOUR_ACCOUNT",
        tax_no="91330000TEST",
        address="YOUR_ACCOUNT",
        phone="YOUR_ACCOUNT",
        bank="YOUR_ACCOUNT",
        bank_account="YOUR_ACCOUNT",
        amount="128.50",
        quantity=1,
        execute=False,
    )

    assert response.success is True
    assert response.command == "order invoice"
    assert response.data["submitted"] is False
    assert response.data["mode"] == "dry-run"
    assert response.data["payload"]["data"]["orderIds"] == ["10001"]
    assert Path(response.data["context_path"]).exists()
