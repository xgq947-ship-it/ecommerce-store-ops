import json

import pytest

from ops_cli.platforms.jst import profit


def test_run_yesterday_profit_requires_template(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="未找到利润统计模板"):
        profit.run_yesterday_profit()


def test_extract_profit_from_payload() -> None:
    payload = {
        "data": {
            "summaryData": {
                "dayList": [
                    {"name": "销售收入", "sumValue": "123.45"},
                    {"name": "经营利润", "sumValue": "929.80"},
                ]
            }
        }
    }

    result = profit.extract_profit_metric(payload)

    assert result == 929.8


def test_run_yesterday_profit_with_template(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "jst").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime" / "context").mkdir(parents=True, exist_ok=True)

    template_path = tmp_path / "data" / "jst" / "profit_yesterday_template.json"
    template_path.write_text(
        json.dumps(
            {
                "method": "POST",
                "url": "https://example.com",
                "headers": {"Cookie": "a=b"},
                "post_data_json": {
                    "data": {
                        "condition": {
                            "shop": [12633507],
                            "shopNames": "（猫超）福安市启明工贸有限公司（肖国清）",
                            "dateType": "senddate",
                            "returnType": "receive_date",
                            "isCkreturnrecDateSendRtmoney": True,
                            "date": ["2026-05-14T16:00:00.000Z", "2026-05-15T15:59:59.999Z"],
                            "olderDate": ["2026-05-14T16:00:00.000Z", "2026-05-15T15:59:59.999Z"],
                            "beginDate": "2026-05-15",
                            "endDate": "2026-05-15",
                        }
                    }
                },
                "defaults": {"store": "（猫超）福安市启明工贸有限公司（肖国清）"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    class FakeResponse:
        status_code = 200
        text = json.dumps(
            {
                "code": 0,
                "data": {
                    "summaryData": {
                        "dayList": [
                            {"name": "经营利润", "sumValue": "929.80"},
                        ]
                    }
                },
            },
            ensure_ascii=False,
        )

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def request(self, method, url, headers=None, json=None):
            return FakeResponse()

    monkeypatch.setattr(profit, "build_client", lambda **kwargs: FakeClient())
    monkeypatch.setattr(profit, "_scene_store_path", lambda site, scene: tmp_path / "scene.json")
    (tmp_path / "scene.json").write_text(
        json.dumps({"headers": {"Cookie": "a=b"}, "method": "POST", "url": "https://example.com"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(profit, "_scene_is_valid", lambda scene_data: {"valid": True, "reason": "ok"})

    result = profit.run_yesterday_profit()

    assert result.data["profit"] == 929.8
    assert result.data["metric_field"] == "经营利润"
    assert result.data["scene"] == "business_profit_multi_dimension_report"


def test_profit_uses_extended_timeout(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "jst").mkdir(parents=True, exist_ok=True)

    template_path = tmp_path / "data" / "jst" / "profit_yesterday_template.json"
    template_path.write_text(
        json.dumps(
            {
                "method": "POST",
                "url": "https://example.com",
                "headers": {"Cookie": "a=b"},
                "post_data_json": {"data": {"condition": {"shop": [12633507]}}},
                "defaults": {"store": "（猫超）福安市启明工贸有限公司（肖国清）"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    captured_kwargs: dict[str, object] = {}

    class FakeResponse:
        status_code = 200
        text = json.dumps(
            {"data": {"summaryData": {"dayList": [{"name": "经营利润", "sumValue": "1.00"}]}}},
            ensure_ascii=False,
        )

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def request(self, method, url, headers=None, json=None):
            return FakeResponse()

    def fake_build_client(**kwargs):
        captured_kwargs.update(kwargs)
        return FakeClient()

    monkeypatch.setattr(profit, "build_client", fake_build_client)
    monkeypatch.setattr(profit, "_scene_store_path", lambda site, scene: tmp_path / "scene.json")
    (tmp_path / "scene.json").write_text(
        json.dumps({"headers": {"Cookie": "a=b"}, "method": "POST", "url": "https://example.com"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(profit, "_scene_is_valid", lambda scene_data: {"valid": True, "reason": "ok"})

    profit.run_yesterday_profit()

    assert captured_kwargs["timeout"] == profit.PROFIT_REQUEST_TIMEOUT
