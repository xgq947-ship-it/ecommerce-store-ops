import json

import pytest

from ops_cli.platforms.tmcs import inventory


def test_tmcs_inventory_export_requires_template(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="未找到猫超库存导出模板"):
        inventory.run_inventory_export()


def test_tmcs_inventory_export_dry_run(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "tmcs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)

    template_path = tmp_path / "data" / "tmcs" / "inventory_export_template.json"
    template_path.write_text(
        json.dumps(
            {
                "defaults": {"output_dir": str(tmp_path / "downloads"), "warehouse_code": "mc_aokesi_suolong"},
                "inventory_search": {"headers": {"cookie": "a=b"}, "method": "POST", "url": "https://example.com/search", "post_data_form": {"warehouseCode": ""}},
                "inventory_export": {"headers": {"cookie": "a=b"}, "method": "POST", "url": "https://example.com/export", "post_data_form": {"warehouseCode": ""}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(inventory, "check_scene_or_fail", lambda *args, **kwargs: {"status": "valid"})

    result = inventory.run_inventory_export(dry_run=True)

    assert result.data["dry_run"] is True
    assert result.data["warehouse_code"] == "mc_aokesi_suolong"
    assert result.data["downloaded"] is False


def test_tmcs_inventory_export_downloads(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "tmcs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)

    template_path = tmp_path / "data" / "tmcs" / "inventory_export_template.json"
    template_path.write_text(
        json.dumps(
            {
                "defaults": {"output_dir": str(tmp_path / "downloads"), "warehouse_code": "mc_aokesi_suolong"},
                "inventory_search": {"headers": {"cookie": "a=b"}, "method": "POST", "url": "https://example.com/search", "post_data_form": {"warehouseCode": ""}},
                "inventory_export": {"headers": {"cookie": "a=b"}, "method": "POST", "url": "https://example.com/export", "post_data_form": {"warehouseCode": ""}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(inventory, "check_scene_or_fail", lambda *args, **kwargs: {"status": "valid"})
    monkeypatch.setattr(
        inventory,
        "_download_inventory_export",
        lambda **kwargs: {
            "output_path": str(tmp_path / "downloads" / "猫超商品库存列表导出.xlsx"),
            "status_code": 200,
            "export_task_id": "task-1",
            "download_url": "https://example.com/file.xlsx",
            "download_size": 128,
        },
    )

    result = inventory.run_inventory_export()

    assert result.data["downloaded"] is True
    assert result.data["warehouse_code"] == "mc_aokesi_suolong"
    assert result.data["output_path"].endswith("猫超商品库存列表导出.xlsx")


def test_tmcs_inventory_learn_uses_dual_browser_flow(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "sessions" / "tmall_chaoshi").mkdir(parents=True, exist_ok=True)

    events: list[tuple[str, object]] = []

    def fake_probe(*, warehouse_code: str) -> dict[str, object]:
        events.append(("probe", warehouse_code))
        return {"status": "captured", "source": "primary_chrome", "warehouse_code": warehouse_code}

    def fake_capture(*, warehouse_code: str, force: bool, primary_probe: dict[str, object]) -> tuple[dict[str, object], dict[str, object], str, str]:
        events.append(("capture", warehouse_code, force, primary_probe["source"]))
        return (
            {"url": "https://example.com/search", "method": "POST", "headers": {"cookie": "a=b"}, "post_data_form": {"warehouseCode": warehouse_code}},
            {"url": "https://example.com/export", "method": "POST", "headers": {"cookie": "a=b"}, "post_data_form": {"warehouseCode": warehouse_code}},
            str(tmp_path / "data" / "sessions" / "tmall_chaoshi" / "maochao_inventory_search.json"),
            str(tmp_path / "data" / "sessions" / "tmall_chaoshi" / "maochao_inventory_export.json"),
        )

    monkeypatch.setattr(inventory, "_probe_primary_chrome_inventory", fake_probe)
    monkeypatch.setattr(inventory, "_capture_inventory_scenes", fake_capture)

    response = inventory.learn_inventory_export()

    assert events == [
        ("probe", "mc_aokesi_suolong"),
        ("capture", "mc_aokesi_suolong", False, "primary_chrome"),
    ]
    assert response.success is True
    assert response.data["primary_probe"]["source"] == "primary_chrome"
    assert response.data["inventory_search_scene"] == "maochao_inventory_search"
    assert response.data["inventory_export_scene"] == "maochao_inventory_export"


def test_tmcs_inventory_primary_probe_reads_chrome_extension_probe_file(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    probe_path = tmp_path / "runtime" / "context" / "tmcs_inventory_primary_probe_latest.json"
    probe_path.parent.mkdir(parents=True, exist_ok=True)
    probe_path.write_text(
        json.dumps(
            {
                "status": "captured",
                "source": "codex_chrome_extension",
                "warehouse_code": "mc_aokesi_suolong",
                "search_request": {"url": "https://example.com/search", "method": "POST"},
                "export_request": {"url": "https://example.com/export", "method": "POST"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(inventory, "get_config", lambda: type("Config", (), {"primary_chrome_cdp_url": ""})())

    probe = inventory._probe_primary_chrome_inventory()

    assert probe["status"] == "captured"
    assert probe["source"] == "codex_chrome_extension"
    assert probe["probe_path"].endswith("tmcs_inventory_primary_probe_latest.json")


def test_tmcs_inventory_template_keeps_sessionhub_cookie(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    path = inventory._write_template(
        search_scene={
            "url": "https://example.com/search",
            "method": "POST",
            "headers": {"content-length": "10", "accept": "application/json"},
            "cookies": [{"name": "sid", "value": "abc"}],
        },
        export_scene={
            "url": "https://example.com/export",
            "method": "POST",
            "headers": {"content-length": "10", "accept": "application/json"},
            "cookies": [{"name": "sid", "value": "abc"}],
        },
    )

    template = json.loads(path.read_text(encoding="utf-8"))
    assert template["inventory_export"]["headers"]["cookie"] == "sid=abc"
    assert "content-length" not in template["inventory_export"]["headers"]


def test_tmcs_inventory_adjust_preview(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "tmcs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "tmcs" / "inventory_adjust_template.json").write_text(
        json.dumps(
            {
                "defaults": {"warehouse_code": "mc_aokesi_suolong"},
                "inventory_search": {"headers": {"cookie": "a=b"}, "method": "POST", "url": "https://example.com/search", "post_data_json": {"_scm_token_": "token"}},
                "inventory_adjust": {
                    "headers": {"cookie": "a=b"},
                    "_scm_token_": "token",
                    "query_sellable_url": "https://example.com/query",
                    "increase_url": "https://example.com/increase",
                    "decrease_url": "https://example.com/decrease",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(inventory, "check_scene_or_fail", lambda *args, **kwargs: {"status": "valid"})
    monkeypatch.setattr(
        inventory,
        "_search_inventory_rows",
        lambda **kwargs: [
            {
                "itemId": 1052534376394,
                "skuId": 6247519890565,
                "storeCode": "mc_aokesi_suolong",
                "downStoreCode": "YPH_d17f9b2d73698bba",
                "scItemId": 787766581354,
                "userId": 725677994,
                "exclusiveInvQuantity": 200,
            }
        ],
    )
    monkeypatch.setattr(inventory, "_query_sellable_quantity", lambda **kwargs: 200)

    result = inventory.run_inventory_adjust(action="increase", sku_adjust=["6247519890565:50"])

    assert result.data["submitted"] is False
    assert result.data["results"][0]["expected_after_total"] == 250
    assert result.data["results"][0]["endpoint"] == "https://example.com/increase"


def test_tmcs_inventory_adjust_clear_uses_sellable_quantity(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "tmcs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "tmcs" / "inventory_adjust_template.json").write_text(
        json.dumps(
            {
                "defaults": {"warehouse_code": "mc_aokesi_suolong"},
                "inventory_search": {"headers": {"cookie": "a=b"}, "method": "POST", "url": "https://example.com/search", "post_data_json": {"_scm_token_": "token"}},
                "inventory_adjust": {
                    "headers": {"cookie": "a=b"},
                    "_scm_token_": "token",
                    "query_sellable_url": "https://example.com/query",
                    "increase_url": "https://example.com/increase",
                    "decrease_url": "https://example.com/decrease",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(inventory, "check_scene_or_fail", lambda *args, **kwargs: {"status": "valid"})
    monkeypatch.setattr(
        inventory,
        "_search_inventory_rows",
        lambda **kwargs: [
            {
                "itemId": 1052534376394,
                "skuId": 6247519890566,
                "storeCode": "mc_aokesi_suolong",
                "downStoreCode": "YPH_d17f9b2d73698bba",
                "scItemId": 787644787653,
                "userId": 725677994,
                "exclusiveInvQuantity": 300,
            }
        ],
    )
    monkeypatch.setattr(inventory, "_query_sellable_quantity", lambda **kwargs: 280)

    result = inventory.run_inventory_adjust(action="clear", sku_id="6247519890566")

    assert result.data["results"][0]["plan_quantity"] == 280
    assert result.data["results"][0]["expected_after_total"] == 20
