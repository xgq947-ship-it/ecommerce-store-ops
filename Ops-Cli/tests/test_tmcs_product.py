import json

import pytest
from openpyxl import Workbook

from ops_cli.platforms.tmcs import product


def _build_goods_workbook(path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "商品列表"
    ws.append(["货品编码", "条码", "名称"])
    for row in rows:
        ws.append(row)
    wb.save(path)


def _build_jst_workbook(path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "商品资料"
    ws.append(["商品编码", "品牌", "名称"])
    for row in rows:
        ws.append(row)
    wb.save(path)


def test_tmcs_product_sync_requires_template(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="未找到猫超商品同步模板"):
        product.run_product_sync()


def test_tmcs_product_sync_use_local_only(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "tmcs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)

    import_path = tmp_path / "猫超商品列表导出.xlsx"
    latest_path = tmp_path / "猫超商品列表导出 (最新）.xlsx"
    jst_path = tmp_path / "聚水潭商品资料（最新）.xlsx"

    _build_goods_workbook(latest_path, [["A1", "OLD-1", "老商品"]])
    _build_goods_workbook(import_path, [["A1", "OLD-1", "老商品"], ["B1", "SKU-B1", "新商品"]])
    _build_jst_workbook(jst_path, [["NEW-SKU-B1", "奥克斯", "匹配商品"]])

    template_path = tmp_path / "data" / "tmcs" / "product_sync_template.json"
    template_path.write_text(
        json.dumps(
            {
                "defaults": {
                    "import_path": str(import_path),
                    "latest_path": str(latest_path),
                    "jst_path": str(jst_path),
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(product, "check_scene_or_fail", lambda *args, **kwargs: {"status": "valid"})
    monkeypatch.setattr(
        product,
        "load_scene_or_fail",
        lambda *args, **kwargs: {
            "headers": {"cookie": "a=b"},
            "method": "POST",
            "url": "https://example.com",
            "post_data_form": {"_scm_token_": "x", "query": "{}"},
        },
    )

    result = product.run_product_sync(use_local_only=True)

    assert result.data["used_backend_export"] is False
    assert result.data["new_rows"] == 1
    assert result.data["output_path"] == str(latest_path)


def test_tmcs_product_sync_force_refresh_downloads(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "tmcs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)

    import_path = tmp_path / "猫超商品列表导出.xlsx"
    latest_path = tmp_path / "猫超商品列表导出 (最新）.xlsx"
    jst_path = tmp_path / "聚水潭商品资料（最新）.xlsx"

    _build_goods_workbook(latest_path, [["A1", "OLD-1", "老商品"]])
    _build_goods_workbook(import_path, [["A1", "OLD-1", "老商品"]])
    _build_jst_workbook(jst_path, [["SKU-B1", "奥克斯", "匹配商品"]])

    downloaded = tmp_path / "downloaded.xlsx"
    _build_goods_workbook(downloaded, [["A1", "OLD-1", "老商品"], ["B1", "BAR-B1", "新商品"]])

    template_path = tmp_path / "data" / "tmcs" / "product_sync_template.json"
    template_path.write_text(
        json.dumps(
            {
                "defaults": {
                    "import_path": str(import_path),
                    "latest_path": str(latest_path),
                    "jst_path": str(jst_path),
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(product, "check_scene_or_fail", lambda *args, **kwargs: {"status": "valid"})
    monkeypatch.setattr(
        product,
        "load_scene_or_fail",
        lambda *args, **kwargs: {
            "headers": {"cookie": "a=b"},
            "method": "POST",
            "url": "https://example.com",
            "post_data_form": {"_scm_token_": "x", "query": "{}"},
        },
    )

    def fake_download_goods_export(**kwargs):
        destination = kwargs["destination"]
        destination.write_bytes(downloaded.read_bytes())
        return {"export_task_id": "task-1", "download_size": len(downloaded.read_bytes())}

    monkeypatch.setattr(product, "_download_goods_export", fake_download_goods_export)

    result = product.run_product_sync(force_refresh=True)

    assert result.data["used_backend_export"] is True
    assert result.data["downloaded"] is True
    assert result.data["new_rows"] == 1
