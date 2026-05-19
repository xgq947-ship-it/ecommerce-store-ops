import json
from pathlib import Path

import pytest

from ops_cli.platforms.jst import stats


def test_run_order_stats_requires_template(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="未找到订单统计模板"):
        stats.run_order_stats()


def test_run_order_stats_with_template(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "jst").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)

    template_path = tmp_path / "data" / "jst" / "order_stats_template.json"
    template_path.write_text(
        json.dumps(
            {
                "method": "POST",
                "url": "https://example.com",
                "headers": {"Cookie": "a=b"},
                "post_data_form": {"__CALLBACKPARAM": "{}"},
                "callback_payload": {"Method": "LoadDataToJSON", "Args": ["1", "[]", "{}"]},
                "metadata": {"captured_for_date": "2026-05-16"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    class FakeResponse:
        status_code = 200
        text = '{"rows":[{"已付款金额":"100.50"},{"已付款金额":"200"}]}'

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def request(self, method, url, headers=None, data=None):
            return FakeResponse()

    monkeypatch.setattr(stats, "build_client", lambda **kwargs: FakeClient())
    monkeypatch.setattr(stats, "_scene_store_path", lambda site, scene: tmp_path / "scene.json")
    (tmp_path / "scene.json").write_text(json.dumps({"headers": {"Cookie": "a=b"}, "method": "POST", "url": "https://example.com"}), encoding="utf-8")
    monkeypatch.setattr(stats, "_scene_is_valid", lambda scene_data: {"valid": True, "reason": "ok"})

    result = stats.run_order_stats()

    assert result.data["order_count"] == 2
    assert result.data["paid_amount"] == 300.5
    assert result.data["scene"] == "profit_multi_dimension_report"


def test_extract_json_payload_supports_wrapped_response() -> None:
    payload = stats._extract_json_payload(
        '0|{"IsSuccess":true,"ReturnValue":"{\\"datas\\":[{\\"已付款金额\\":\\"123.45\\"}]}"}'
    )

    assert payload["datas"][0]["已付款金额"] == "123.45"
