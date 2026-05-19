from __future__ import annotations

import json
import sys
import time as time_module
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ops_cli.config import get_config
from ops_cli.integrations.sessionhub import get_scene_manager
from ops_cli.output import CommandResponse
from ops_cli.runtime_context import write_runtime_context
from ops_cli.utils.http import build_client


JST_SITE = "jst_erp"
BASE_ORDER_SCENE = "order_list"
PROFIT_SCENE = "business_profit_multi_dimension_report"
TARGET_URL = "https://ss.erp321.com/profit-report/multi-dimension"
PROFIT_API_URL_PART = "GetMultipleDimensionsData"
DEFAULT_METRIC_FIELD = "经营利润"
TEMPLATE_PATH = Path("data/jst/profit_yesterday_template.json")
STORE_NAME = "（猫超）福安市启明工贸有限公司（肖国清）"
TIME_TYPE_TEXT = "订单发货时间"
RETURN_TYPE_TEXT = "以进仓时间统计"
TIME_TYPE_VALUE = "senddate"
RETURN_TYPE_VALUE = "receive_date"
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
PROFIT_REQUEST_TIMEOUT = 60.0


def _sessionhub_root() -> Path:
    return Path(get_config().sessionhub_root).expanduser().resolve()


def _scene_store_path(site: str, scene: str) -> Path:
    return _sessionhub_root() / "data" / "sessions" / site / f"{scene}.json"


def _template_path() -> Path:
    return Path.cwd() / TEMPLATE_PATH


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _merge_cookie_header(headers: dict[str, Any], cookies: list[dict[str, Any]] | None) -> dict[str, str]:
    merged = {str(key): str(value) for key, value in headers.items() if str(key).lower() != "cookie"}
    if cookies:
        merged["cookie"] = "; ".join(
            f"{cookie.get('name')}={cookie.get('value')}"
            for cookie in cookies
            if cookie.get("name")
        )
    return merged


def _extract_json_payload(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        raise RuntimeError("接口返回为空")
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"无法解析利润接口响应：{stripped[:300]}") from exc


def _extract_numeric(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    filtered = "".join(char for char in text if char.isdigit() or char in ".-")
    if not filtered:
        return None
    try:
        return float(filtered)
    except ValueError:
        return None


def extract_profit_metric(payload: dict[str, Any]) -> float:
    rows = (((payload.get("data") or {}).get("summaryData") or {}).get("dayList") or [])
    if not isinstance(rows, list):
        raise RuntimeError("利润接口缺少 summaryData.dayList")
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("name") or "").strip() != DEFAULT_METRIC_FIELD:
            continue
        value = _extract_numeric(row.get("sumValue"))
        if value is None:
            raise RuntimeError("经营利润字段存在，但数值为空")
        return round(value, 2)
    raise RuntimeError("未在利润接口返回中找到“经营利润”字段")


def _scene_is_valid(scene_data: dict[str, Any]) -> dict[str, Any]:
    headers = _merge_cookie_header(
        dict(scene_data.get("headers") or {}),
        scene_data.get("cookies") or [],
    )
    method = str(scene_data.get("method") or "POST").upper()
    url = str(scene_data.get("url") or TARGET_URL)
    post_data_json = scene_data.get("post_data_json") or None
    with build_client(follow_redirects=True, timeout=PROFIT_REQUEST_TIMEOUT) as client:
        response = client.request(method, url, headers=headers, json=post_data_json)
    payload = _extract_json_payload(response.text)
    profit = extract_profit_metric(payload)
    return {
        "status_code": response.status_code,
        "profit": profit,
        "valid": response.status_code == 200,
        "reason": "接口返回 200，scene 可用" if response.status_code == 200 else f"接口返回 {response.status_code}",
    }


def _load_template() -> dict[str, Any]:
    path = _template_path()
    if not path.exists():
        raise RuntimeError(f"未找到利润统计模板：{path}。请先运行 `ops jst profit learn`。")
    return _read_json(path)


def _save_scene_data(payload: dict[str, Any]) -> Path:
    path = _scene_store_path(JST_SITE, PROFIT_SCENE)
    _write_json(path, payload)
    return path


def _yesterday_value() -> date:
    return date.today() - timedelta(days=1)


def _date_range_payload(target_date: date) -> tuple[list[str], list[str], str, str]:
    start_local = datetime.combine(target_date, time.min, tzinfo=SHANGHAI_TZ)
    end_local = datetime.combine(target_date, time.max.replace(microsecond=999000), tzinfo=SHANGHAI_TZ)
    start_utc = start_local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_utc = end_local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.999Z")
    local_date = target_date.isoformat()
    return [start_utc, end_utc], [start_utc, end_utc], local_date, local_date


def _write_template(*, scene_data: dict[str, Any], store: str) -> Path:
    payload = deepcopy(scene_data.get("post_data_json") or {})
    condition = (((payload.get("data") or {}).get("condition")) or {})
    template = {
        "site": JST_SITE,
        "scene": PROFIT_SCENE,
        "capture_source": "sessionhub_9222",
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "url": scene_data.get("url"),
        "method": scene_data.get("method"),
        "headers": _merge_cookie_header(
            dict(scene_data.get("headers") or {}),
            scene_data.get("cookies") or [],
        ),
        "post_data_json": payload,
        "defaults": {
            "store": store,
            "shop_ids": list(condition.get("shop") or []),
            "metric_field": DEFAULT_METRIC_FIELD,
            "date_type_text": TIME_TYPE_TEXT,
            "date_type_value": condition.get("dateType") or TIME_TYPE_VALUE,
            "return_type_text": RETURN_TYPE_TEXT,
            "return_type_value": condition.get("returnType") or RETURN_TYPE_VALUE,
            "return_stat_flag": bool(condition.get("isCkreturnrecDateSendRtmoney")),
        },
    }
    path = _template_path()
    _write_json(path, template)
    return path


def _apply_payload_overrides(template: dict[str, Any], *, target_date: date, store: str) -> dict[str, Any]:
    payload = deepcopy(template.get("post_data_json") or {})
    condition = ((payload.setdefault("data", {})).setdefault("condition", {}))
    defaults = template.get("defaults") or {}
    shop_ids = list(defaults.get("shop_ids") or condition.get("shop") or [])
    date_range, older_date_range, begin_date, end_date = _date_range_payload(target_date)
    condition["shop"] = shop_ids
    condition["shopNames"] = store
    condition["dateType"] = defaults.get("date_type_value") or TIME_TYPE_VALUE
    condition["returnType"] = defaults.get("return_type_value") or RETURN_TYPE_VALUE
    condition["isCkreturnrecDateSendRtmoney"] = bool(defaults.get("return_stat_flag", True))
    condition["date"] = date_range
    condition["olderDate"] = older_date_range
    condition["beginDate"] = begin_date
    condition["endDate"] = end_date
    return payload


def _apply_profit_filters(page: Any, *, store: str) -> None:
    page.locator('span[title="订单支付时间"]').click(force=True)
    page.get_by_text(TIME_TYPE_TEXT, exact=True).click(timeout=5000)
    page.wait_for_timeout(500)
    page.locator('span[title="以订单实时统计"]').click(force=True)
    page.get_by_text(RETURN_TYPE_TEXT, exact=True).click(timeout=5000)
    page.wait_for_timeout(500)
    page.locator("#shop").click(timeout=5000)
    page.wait_for_timeout(500)
    page.get_by_text(store, exact=True).click(timeout=5000)
    page.get_by_text("确 定", exact=True).click(timeout=5000)
    page.wait_for_timeout(1000)
    page.locator('input[placeholder="自定义"]').click(timeout=5000)
    page.get_by_text("昨天", exact=True).click(timeout=5000)
    page.wait_for_timeout(800)


def _capture_profit_scene(*, store: str) -> dict[str, Any]:
    get_scene_manager().ensure_scene(JST_SITE, BASE_ORDER_SCENE)
    root = _sessionhub_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from scene.chrome_cdp import CDP_URL, start_chrome  # type: ignore
    from playwright.sync_api import Error as PlaywrightError  # type: ignore
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError  # type: ignore
    from playwright.sync_api import sync_playwright  # type: ignore

    ok, msg = start_chrome()
    if not ok:
        raise RuntimeError(msg)

    captured: dict[str, Any] | None = None

    def on_request(request: Any) -> None:
        nonlocal captured
        if captured is not None:
            return
        if request.method.upper() != "POST":
            return
        if PROFIT_API_URL_PART not in request.url:
            return
        post_data_json = request.post_data_json or {}
        condition = (((post_data_json.get("data") or {}).get("condition")) or {})
        if not condition.get("shop"):
            return
        captured = {
            "site": JST_SITE,
            "scene": PROFIT_SCENE,
            "status": "captured",
            "source": "sessionhub_9222",
            "url": request.url,
            "method": request.method.upper(),
            "headers": dict(request.headers),
            "post_data": request.post_data,
            "post_data_json": post_data_json,
            "post_data_form": None,
            "cookies": [],
            "tokens": {},
            "meta": {
                "captured_at": datetime.now().isoformat(timespec="seconds"),
                "target_url": TARGET_URL,
                "default_store": store,
                "time_type_text": TIME_TYPE_TEXT,
                "return_type_text": RETURN_TYPE_TEXT,
            },
        }

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except PlaywrightError as exc:
            raise RuntimeError(f"连接 9222 Chrome 失败：{exc}") from exc
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()
        context.on("request", on_request)
        try:
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        except PlaywrightTimeoutError:
            pass
        page.wait_for_timeout(3000)
        _apply_profit_filters(page, store=store)
        page.get_by_text("查 询", exact=True).click(timeout=5000, force=True)
        deadline = datetime.now().timestamp() + 45
        while captured is None and datetime.now().timestamp() < deadline:
            page.wait_for_timeout(1000)
        if captured is None:
            raise RuntimeError("未捕获到利润统计请求。请确认 9222 Chrome 已登录聚水潭，并且页面可正常查询。")
        try:
            captured["cookies"] = context.cookies([captured["url"]])
        except Exception:
            captured["cookies"] = context.cookies()

    _save_scene_data(captured)
    return captured


def learn_jst_profit_scene(*, force: bool = False) -> CommandResponse:
    store = get_config().jst_order_stats_store or STORE_NAME
    scene_path = _scene_store_path(JST_SITE, PROFIT_SCENE)
    inputs = {"site": JST_SITE, "scene": PROFIT_SCENE, "force": force, "store": store}

    if scene_path.exists() and not force:
        scene_data = _read_json(scene_path)
        try:
            check = _scene_is_valid(scene_data)
            if check["valid"]:
                template_path = _write_template(scene_data=scene_data, store=store)
                context_path = write_runtime_context(
                    task_name="jst_profit_learn",
                    status="success",
                    inputs=inputs,
                    outputs={"scene_path": str(scene_path), "template_path": str(template_path), "reuse": True},
                    artifacts=[str(scene_path), str(template_path)],
                )
                return CommandResponse(
                    success=True,
                    platform="jst",
                    command="profit learn",
                    data={
                        "site": JST_SITE,
                        "scene": PROFIT_SCENE,
                        "source": "existing_scene",
                        "scene_path": str(scene_path),
                        "template_path": str(template_path),
                        "context_path": str(context_path),
                        "next_command": "ops --json jst profit yesterday",
                    },
                )
        except Exception:
            pass

    captured = _capture_profit_scene(store=store)
    template_path = _write_template(scene_data=captured, store=store)
    last_error: Exception | None = None
    check: dict[str, Any] | None = None
    for wait_seconds in (0, 2, 4):
        if wait_seconds:
            time_module.sleep(wait_seconds)
        try:
            scene_data = _read_json(scene_path)
            check = _scene_is_valid(scene_data)
            break
        except Exception as exc:
            last_error = exc
    if check is None:
        raise last_error or RuntimeError("利润 scene 复检失败")
    context_path = write_runtime_context(
        task_name="jst_profit_learn",
        status="success" if check["valid"] else "failed",
        inputs=inputs,
        outputs={"scene_path": str(scene_path), "template_path": str(template_path), "check": check},
        artifacts=[str(scene_path), str(template_path)],
    )
    if not check["valid"]:
        raise RuntimeError(f"scene 已捕获，但复检失败：{check['reason']}")
    return CommandResponse(
        success=True,
        platform="jst",
        command="profit learn",
        data={
            "site": JST_SITE,
            "scene": PROFIT_SCENE,
            "source": "sessionhub_9222",
            "scene_path": str(scene_path),
            "template_path": str(template_path),
            "context_path": str(context_path),
            "next_command": "ops --json jst profit yesterday",
        },
    )


def run_yesterday_profit() -> CommandResponse:
    target_date = _yesterday_value()
    selected_store = get_config().jst_order_stats_store or STORE_NAME
    template = _load_template()
    scene_path = _scene_store_path(JST_SITE, PROFIT_SCENE)
    if not scene_path.exists():
        raise RuntimeError(f"未找到利润 scene：{scene_path}。请先运行 `ops jst profit learn`。")
    scene_check = _scene_is_valid(_read_json(scene_path))
    if not scene_check["valid"]:
        raise RuntimeError(f"利润 scene 不可用：{scene_check['reason']}。请先运行 `ops jst profit learn`。")

    payload = _apply_payload_overrides(template, target_date=target_date, store=selected_store)
    headers = dict(template.get("headers") or {})
    method = str(template.get("method") or "POST").upper()
    url = str(template.get("url") or TARGET_URL)
    with build_client(follow_redirects=True, timeout=PROFIT_REQUEST_TIMEOUT) as client:
        response = client.request(method, url, headers=headers, json=payload)
    parsed = _extract_json_payload(response.text)
    profit_value = extract_profit_metric(parsed)
    context_path = write_runtime_context(
        task_name="jst_profit_yesterday_run",
        status="success",
        inputs={"date": target_date.isoformat(), "store": selected_store, "scene": PROFIT_SCENE},
        outputs={"profit": profit_value, "status_code": response.status_code},
    )
    return CommandResponse(
        success=True,
        platform="jst",
        command="profit yesterday",
        data={
            "date": target_date.isoformat(),
            "store": selected_store,
            "profit": profit_value,
            "metric_field": DEFAULT_METRIC_FIELD,
            "scene": PROFIT_SCENE,
            "source": "sessionhub",
            "context_path": str(context_path),
            "request": {"url": url, "method": method, "payload": payload},
        },
    )


def get_yesterday_profit() -> CommandResponse:
    return run_yesterday_profit()


def get_month_profit() -> CommandResponse:
    return CommandResponse(
        success=True,
        platform="jst",
        command="profit month",
        data={"month": "current", "profit": 45678.9, "currency": "CNY", "mode": "mock"},
    )
