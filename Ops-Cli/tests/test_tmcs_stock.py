from __future__ import annotations

from ops_cli.platforms.tmcs import stock


def test_query_stock_maps_inventory_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        stock,
        "_load_stock_template",
        lambda: {
            "defaults": {"warehouse_code": "mc_aokesi_suolong"},
            "inventory_search": {"url": "https://example.test/search", "headers": {}},
        },
    )
    monkeypatch.setattr(stock, "check_scene_or_fail", lambda *args, **kwargs: {"status": "valid"})

    def fake_search_inventory_rows(*, search_scene, warehouse_code, item_id=None, sku_id=None):
        assert warehouse_code == "mc_aokesi_suolong"
        assert sku_id is None
        if item_id == "1052534376394":
            return [
                {
                    "itemId": 1052534376394,
                    "skuId": 6247519890565,
                    "supplierScItemId": "SG-001",
                    "scItemId": "PLATFORM-001",
                    "barCode": "BAR-001",
                    "merchantGoodsCode": "AOK-SKU-001",
                    "storeCode": "mc_aokesi_suolong",
                }
            ]
        return []

    monkeypatch.setattr(stock, "_search_inventory_rows", fake_search_inventory_rows)

    rows = stock.query_stock(item_ids=["1052534376394", "missing"], warehouse_code="mc_aokesi_suolong")

    assert rows == [
        {
            "platform_item_id": "1052534376394",
            "platform_sku_id": "6247519890565",
            "supplier_goods_id": "SG-001",
            "merchant_goods_code": "BAR-001",
        }
    ]


def test_normalize_item_ids_dedupes_and_preserves_order() -> None:
    assert stock.normalize_item_ids(" 123,234,123,,345 ") == ["123", "234", "345"]


def test_standardize_stock_row_prefers_supplier_side_goods_id() -> None:
    row = {
        "itemId": 1053519004987,
        "skuId": 6087220948149,
        "supplierScItemId": 1040893114685,
        "scItemId": 1052514261839,
        "barCode": "SUZBHLYZHH1001A",
        "merchantGoodsCode": "SUZBHLYZHH1001",
    }

    assert stock.standardize_stock_row(row) == {
        "platform_item_id": "1053519004987",
        "platform_sku_id": "6087220948149",
        "supplier_goods_id": "1040893114685",
        "merchant_goods_code": "SUZBHLYZHH1001A",
    }
