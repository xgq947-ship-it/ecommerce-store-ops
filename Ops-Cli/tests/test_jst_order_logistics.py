import json
from pathlib import Path
from typing import Any

from ops_cli.platforms.jst import order


class FakeSceneManager:
    root = "/tmp/sessionhub"

    def ensure_scene(self, site: str, scene: str) -> dict[str, Any]:
        return {
            "site": site,
            "scene": scene,
            "url": "https://www.erp321.com/app/order/order/list.aspx",
            "headers": {"Cookie": "sid=test"},
        }


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.text = json.dumps(payload, ensure_ascii=False)

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return json.loads(self.text)


class FakeClient:
    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def post(self, *args: object, **kwargs: object) -> FakeResponse:
        payload = str((kwargs or {}).get("data") or "")
        order_no = "TB10001"
        if "TB40404" in payload:
            order_no = "TB40404"
        rows = [
            {
                "o_id": "10001",
                "so_id": "SO10001",
                "outer_so_id": order_no,
                "logistics_no": "SF123456",
                "logistics_company": "顺丰速运",
                "logistics_status": "已签收",
            }
        ]
        if order_no == "TB40404":
            rows = []
        return FakeResponse({"ReturnValue": json.dumps({"rows": rows}, ensure_ascii=False)})


def test_guess_signed_from_status() -> None:
    assert order._guess_signed("包裹已签收", []) is True
    assert order._guess_signed("", []) is None


def test_normalize_trace_events_from_nested_payload() -> None:
    events = order._normalize_trace_events({"data": [{"time": "10:00", "content": "已揽收"}]})

    assert events == [{"time": "10:00", "content": "已揽收"}]


def test_trace_authorization_challenge_is_not_treated_as_empty_trace() -> None:
    payload = {
        "IsSuccess": False,
        "ReturnValue": {
            "msg": "为了您的数据安全，查询轨迹要求验证身份，已发送验证码到您手机",
            "action": "查询轨迹",
        },
    }
    response = "0|" + json.dumps(payload, ensure_ascii=False)

    try:
        order._parse_acall_response(response)
    except order.LogisticsTraceAuthorizationRequired as exc:
        assert "查询轨迹需要完成短信验证" in str(exc)
    else:
        raise AssertionError("应将查询轨迹短信验证识别为授权错误")


def test_run_order_logistics_from_order_list(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(order, "get_scene_manager", lambda: FakeSceneManager())
    monkeypatch.setattr(order, "build_client", lambda **kwargs: FakeClient())

    response = order.run_order_logistics(outer_order_id="TB10001")

    assert response.success is True
    assert response.command == "order logistics"
    assert response.data["matched_filter"] == "outer_so_id"
    assert response.data["logistics_no"] == "SF123456"
    assert response.data["logistics_company"] == "顺丰速运"
    assert response.data["signed"] is True
    assert Path(response.data["context_path"]).exists()


def test_run_order_logistics_batch(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(order, "get_scene_manager", lambda: FakeSceneManager())
    monkeypatch.setattr(order, "build_client", lambda **kwargs: FakeClient())

    response = order.run_order_logistics(outer_order_ids=["TB10001", "TB40404"])

    assert response.success is False
    assert response.command == "order logistics"
    assert response.data["summary"] == {"total": 2, "success": 1, "failed": 1}
    assert response.data["items"][0]["success"] is True
    assert response.data["items"][0]["outer_order_id"] == "TB10001"
    assert response.data["items"][1]["success"] is False
    assert response.data["items"][1]["outer_order_id"] == "TB40404"
    assert "聚水潭未找到指定订单" in response.data["items"][1]["error"]
    assert Path(response.data["context_path"]).exists()


def test_normalize_orders_supports_text_input(tmp_path: Path) -> None:
    input_path = tmp_path / "orders.txt"
    input_path.write_text("TB10001\nTB10002\n\nTB10001\n", encoding="utf-8")

    orders, resolved_input = order._normalize_orders(order_ids=[], input_path=str(input_path), limit=2)

    assert orders == ["TB10001", "TB10002"]
    assert resolved_input == str(input_path.resolve())
