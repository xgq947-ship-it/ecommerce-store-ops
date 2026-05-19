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
        rows = [
            {
                "o_id": "10001",
                "so_id": "SO10001",
                "outer_so_id": "TB10001",
                "logistics_no": "SF123456",
                "logistics_company": "顺丰速运",
                "logistics_status": "已签收",
            }
        ]
        return FakeResponse({"ReturnValue": json.dumps({"rows": rows}, ensure_ascii=False)})


def test_guess_signed_from_status() -> None:
    assert order._guess_signed("包裹已签收", []) is True
    assert order._guess_signed("", []) is None


def test_normalize_trace_events_from_nested_payload() -> None:
    events = order._normalize_trace_events({"data": [{"time": "10:00", "content": "已揽收"}]})

    assert events == [{"time": "10:00", "content": "已揽收"}]


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
