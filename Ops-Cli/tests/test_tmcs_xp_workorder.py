from __future__ import annotations

import pytest

from ops_cli.capabilities import capability_ids, get_capability
from ops_cli.platforms.tmcs import xp_workorder


def test_xp_workorder_capability_registered() -> None:
    registered = capability_ids()
    assert "tmcs.xp-workorder.count" in registered
    assert "tmcs.xp-workorder.learn" in registered

    spec = get_capability("tmcs.xp-workorder.count")
    assert spec.platform == "tmcs"
    assert spec.command == "xp-workorder count"
    assert "xp_workorder_count" in spec.scenes


def test_extract_count_from_top_level_total() -> None:
    payload = {"data": {"totalCount": 7, "rows": []}}
    assert xp_workorder.extract_workorder_count(payload) == 7


def test_extract_count_from_nested_pending() -> None:
    payload = {"result": {"summary": {"pendingCount": "12"}}}
    assert xp_workorder.extract_workorder_count(payload) == 12


def test_extract_count_falls_back_to_rows_length() -> None:
    payload = {"data": {"rows": [{"a": 1}, {"a": 2}, {"a": 3}]}}
    assert xp_workorder.extract_workorder_count(payload) == 3


def test_extract_count_missing_returns_none() -> None:
    payload = {"data": {"foo": "bar"}}
    assert xp_workorder.extract_workorder_count(payload) is None


def test_count_dry_run_returns_simulated(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)

    response = xp_workorder.count_xp_workorders(threshold=4, dry_run=True)

    assert response.success is True
    assert response.platform == "tmcs"
    assert response.command == "xp-workorder count"
    data = response.data
    assert data["count"] == 0
    assert data["threshold"] == 4
    assert data["exceeded"] is False
    assert data["source"] == "simulated"
    assert data["simulated"] is True
    assert data["dry_run"] is True
    assert data["scene"].endswith("/xp_workorder_count")
    assert data["context_path"].endswith(".json")


def test_count_reads_scene_and_returns_exceeded(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)

    scene = {
        "url": "https://example.com/xp/list",
        "method": "POST",
        "headers": {"content-type": "application/json"},
        "post_data_json": {"pageIndex": 1, "pageSize": 10},
        "cookies": [],
    }
    monkeypatch.setattr(xp_workorder, "load_scene_or_fail", lambda *a, **kw: scene)
    monkeypatch.setattr(xp_workorder, "check_scene_or_fail", lambda *a, **kw: {"status": "valid"})

    def fake_request(method, url, *, headers, json_body=None, data_body=None, params=None, timeout=120.0):
        assert method == "POST"
        assert url == "https://example.com/xp/list"
        assert json_body == {"pageIndex": 1, "pageSize": 10}
        return 200, {"data": {"totalCount": 5}}, b""

    monkeypatch.setattr(xp_workorder, "tmcs_request", fake_request)

    response = xp_workorder.count_xp_workorders(threshold=4, dry_run=False)

    assert response.success is True
    data = response.data
    assert data["count"] == 5
    assert data["threshold"] == 4
    assert data["exceeded"] is True
    assert data["source"] == "api"
    assert data["simulated"] is False
    assert data["dry_run"] is False


def test_count_below_threshold_not_exceeded(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        xp_workorder,
        "load_scene_or_fail",
        lambda *a, **kw: {"url": "https://example.com/", "method": "GET", "headers": {}, "cookies": []},
    )
    monkeypatch.setattr(xp_workorder, "check_scene_or_fail", lambda *a, **kw: {"status": "valid"})
    monkeypatch.setattr(
        xp_workorder,
        "tmcs_request",
        lambda *a, **kw: (200, {"data": {"totalCount": 3}}, b""),
    )

    response = xp_workorder.count_xp_workorders(threshold=4, dry_run=False)
    assert response.data["count"] == 3
    assert response.data["exceeded"] is False


def test_count_missing_field_raises_workorder_not_found(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        xp_workorder,
        "load_scene_or_fail",
        lambda *a, **kw: {"url": "https://example.com/", "method": "GET", "headers": {}, "cookies": []},
    )
    monkeypatch.setattr(xp_workorder, "check_scene_or_fail", lambda *a, **kw: {"status": "valid"})
    monkeypatch.setattr(xp_workorder, "tmcs_request", lambda *a, **kw: (200, {"data": {"foo": "bar"}}, b""))

    with pytest.raises(RuntimeError, match="WORKORDER_COUNT_NOT_FOUND"):
        xp_workorder.count_xp_workorders(threshold=4, dry_run=False)
