import json
from datetime import date

import pytest

from ops_cli.platforms.tmcs import bill


def test_tmcs_bill_last_month_query_window_extends_three_days(monkeypatch) -> None:
    monkeypatch.setattr(bill, "previous_month_range", lambda: ("2026-04-01", "2026-04-30"))

    begin, finish, query_finish = bill._normalize_dates(start=None, end=None, last_month=True)

    assert begin == date(2026, 4, 1)
    assert finish == date(2026, 4, 30)
    assert query_finish == date(2026, 5, 3)


def test_tmcs_bill_download_requires_template(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="未找到猫超账单下载模板"):
        bill.run_bill_download(last_month=True)


def test_tmcs_bill_download_dry_run(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "tmcs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)

    template_path = tmp_path / "data" / "tmcs" / "bill_download_template.json"
    template_path.write_text(
        json.dumps({"defaults": {"output_dir": str(tmp_path / "downloads")}}, ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(bill, "check_scene_or_fail", lambda *args, **kwargs: {"status": "valid"})

    result = bill.run_bill_download(start="2026-05-01", end="2026-05-16", dry_run=True)

    assert result.data["dry_run"] is True
    assert result.data["bill_count"] == 0


def test_tmcs_bill_download_last_month(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "tmcs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)

    template_path = tmp_path / "data" / "tmcs" / "bill_download_template.json"
    template_path.write_text(
        json.dumps(
            {
                "defaults": {"output_dir": str(tmp_path / "downloads")},
                "statement_export": {"headers": {"cookie": "a=b"}, "method": "POST", "url": "https://example.com", "post_data_form": {"_scm_token_": "x", "query": "{}"}},
                "download_query": {"headers": {"cookie": "a=b"}, "method": "POST", "url": "https://example.com/query", "post_data_json": {"parameters": [{"pageIndex": 1, "pageSize": 20}], "_scm_token_": "x"}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(bill, "check_scene_or_fail", lambda *args, **kwargs: {"status": "valid"})
    monkeypatch.setattr(
        bill,
        "_list_bill_items",
        lambda **kwargs: [{"billCode": "HDB202605012026051632979767827-1603202"}],
    )
    monkeypatch.setattr(
        bill,
        "_download_bill_file",
        lambda **kwargs: tmp_path / "downloads" / "HDB202605012026051632979767827-1603202.xlsx",
    )

    result = bill.run_bill_download(last_month=True)

    assert result.data["bill_count"] == 1
    assert result.data["query_grace_days"] == 3
    assert result.data["downloaded_files"][0].endswith(".xlsx")


def test_tmcs_bill_download_statement_list(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "tmcs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)

    template_path = tmp_path / "data" / "tmcs" / "bill_download_template.json"
    template_path.write_text(
        json.dumps(
            {
                "defaults": {"output_dir": str(tmp_path / "downloads")},
                "statement_export": {"headers": {"cookie": "a=b"}, "method": "POST", "url": "https://example.com", "post_data_form": {"_scm_token_": "x", "query": "{}"}},
                "download_query": {"headers": {"cookie": "a=b"}, "method": "POST", "url": "https://example.com/query", "post_data_json": {"parameters": [{"pageIndex": 1, "pageSize": 20}], "_scm_token_": "x"}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(bill, "check_scene_or_fail", lambda *args, **kwargs: {"status": "valid"})
    monkeypatch.setattr(bill, "_list_bill_items", lambda **kwargs: [])
    monkeypatch.setattr(bill, "_download_statement_list", lambda **kwargs: tmp_path / "downloads" / "对账单列表.xlsx")

    result = bill.run_bill_download(start="2026-05-01", end="2026-05-16", download_statement_list=True)

    assert result.data["statement_list_path"].endswith("对账单列表.xlsx")
