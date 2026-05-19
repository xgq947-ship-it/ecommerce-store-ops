from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ops_cli.integrations.sessionhub import get_scene_manager
from ops_cli.output import CommandResponse
from ops_cli.platforms.jst.order import DEFAULT_JST_ORDER_PATH
from ops_cli.platforms.jst.order import JST_ORDER_SCENE
from ops_cli.platforms.jst.order import JST_SITE
from ops_cli.platforms.jst.order import ORDER_ID_FILTER_KEYS
from ops_cli.platforms.jst.order import OUTER_ORDER_FILTER_KEY
from ops_cli.platforms.jst.order import _extract_form_template
from ops_cli.platforms.jst.order import _first_text
from ops_cli.platforms.jst.order import _query_order_rows
from ops_cli.platforms.jst.order import _query_order_rows_by_identifier
from ops_cli.runtime_context import write_runtime_context
from ops_cli.utils.http import build_client


JST_ORDER_INVOICE_SCENE = "order_invoice_workorder"
TEMPLATE_PATH = Path("data/jst/order_invoice_workorder_template.json")
BATCH_INSERT_URL = "https://api.erp321.com/jgd/api/gd/workOrder/batchInsert"
WORKORDER_ORIGIN = "https://shouhou.erp321.com"
WORKORDER_REFERER = "https://shouhou.erp321.com/"
WORKORDER_TITLE = "发票"
DEFAULT_INVOICE_TYPE = "专用发票"
DEFAULT_QUANTITY = 1
DEFAULT_WORKORDER_TYPE_ID = "invoice"
DEFAULT_WORKORDER_SOURCE = "PC_ORDER"
DEFAULT_GRADE = "NORMAL"
DEFAULT_FIELD_MAP = {
    "invoice_type": "invoiceTypeField",
    "title": "invoiceTitleField",
    "tax_no": "invoiceTaxNoField",
    "address": "invoiceAddressField",
    "phone": "invoicePhoneField",
    "bank": "invoiceBankField",
    "bank_account": "invoiceBankAccountField",
    "quantity": "invoiceQuantityField",
    "amount": "invoiceAmountField",
    "order": "orderField",
}


def _template_path() -> Path:
    return Path.cwd() / TEMPLATE_PATH


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _money(value: str | Decimal) -> Decimal:
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise RuntimeError("--amount 必须是合法金额") from exc
    if amount <= 0:
        raise RuntimeError("--amount 必须大于 0")
    return amount.quantize(Decimal("0.01"))


def _validate_required(**values: str) -> None:
    missing = [name for name, value in values.items() if not str(value or "").strip()]
    if missing:
        raise RuntimeError(f"缺少必填发票信息：{', '.join(missing)}")


def _extract_cookie_value(headers: dict[str, str], name: str) -> str:
    cookie = headers.get("Cookie") or headers.get("cookie") or ""
    for part in cookie.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key == name:
            return value
    return ""


def _api_headers(session: dict[str, Any], template_headers: dict[str, Any] | None = None) -> dict[str, str]:
    source_headers = {str(key): str(value) for key, value in (session.get("headers") or {}).items()}
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": WORKORDER_ORIGIN,
        "Referer": WORKORDER_REFERER,
    }
    for key, value in (template_headers or {}).items():
        key_text = str(key)
        if key_text.lower() in {"authorization", "cookie", "content-length", "host"}:
            continue
        headers[key_text] = str(value)
    for key in ("User-Agent", "user-agent", "X-Requested-With", "x-requested-with"):
        value = source_headers.get(key)
        if value:
            canonical = "-".join(part.capitalize() for part in key.split("-"))
            headers[canonical] = value
    u_sso_token = _extract_cookie_value(source_headers, "u_sso_token")
    if u_sso_token:
        headers["u_sso_token"] = u_sso_token
    return headers


def _online_order_id(row: dict[str, Any]) -> str:
    for key in ("so_id", "raw_so_id", "pre_so_id"):
        value = str(row.get(key) or "").strip()
        if value.startswith("LP"):
            return value
    return _first_text(row, ("so_id", "raw_so_id", "pre_so_id"))


def _resolve_order_identity(order_id: str, outer_order_id: str | None = None) -> dict[str, str]:
    session = get_scene_manager().ensure_scene(JST_SITE, JST_ORDER_SCENE)
    headers = dict(session.get("headers") or {})
    cookie = str(headers.get("Cookie") or headers.get("cookie") or "").strip()
    if not cookie:
        raise RuntimeError("SessionHub 已返回 session，但缺少 Cookie。请重新捕获聚水潭会话。")
    url = str(session.get("url") or f"https://www.erp321.com{DEFAULT_JST_ORDER_PATH}").strip()
    form_template = _extract_form_template(session)

    with build_client(follow_redirects=True, timeout=60.0) as client:
        rows, filter_key = _query_order_rows_by_identifier(client, url, cookie, order_id, outer_order_id, form_template)
        if not rows and order_id and not outer_order_id:
            rows = _query_order_rows(client, url, cookie, OUTER_ORDER_FILTER_KEY, order_id, form_template)
            filter_key = OUTER_ORDER_FILTER_KEY
    if not rows:
        raise RuntimeError("聚水潭未找到指定订单")
    if len(rows) > 1:
        raise RuntimeError(f"聚水潭返回 {len(rows)} 条订单，请换更精确的订单号")
    row = rows[0]
    internal_order_id = str(row.get("o_id") or "").strip()
    online_order_id = _online_order_id(row)
    if not internal_order_id:
        raise RuntimeError("聚水潭订单缺少 o_id，无法创建工单")
    return {
        "order_id": order_id,
        "outer_order_id": outer_order_id or "",
        "matched_filter": filter_key,
        "internal_order_id": internal_order_id,
        "online_order_id": online_order_id,
    }


def build_invoice_workorder_payload(
    *,
    order_id: str,
    internal_order_id: str,
    online_order_id: str,
    invoice_type: str,
    title: str,
    tax_no: str,
    address: str,
    phone: str,
    bank: str,
    bank_account: str,
    amount: Decimal,
    quantity: int,
    field_map: dict[str, str] | None = None,
    workorder_type_id: str = DEFAULT_WORKORDER_TYPE_ID,
) -> dict[str, Any]:
    fields = {**DEFAULT_FIELD_MAP, **(field_map or {})}
    begin_time = datetime.now().replace(microsecond=0)
    end_time = begin_time + timedelta(days=3)
    business_fields = [
        {"fieldId": fields["invoice_type"], "value": invoice_type},
        {"fieldId": fields["title"], "value": title},
        {"fieldId": fields["tax_no"], "value": tax_no},
        {"fieldId": fields["address"], "value": address},
        {"fieldId": fields["phone"], "value": phone},
        {"fieldId": fields["bank"], "value": bank},
        {"fieldId": fields["bank_account"], "value": bank_account},
        {"fieldId": fields["quantity"], "value": quantity},
        {"fieldId": fields["amount"], "value": float(amount)},
        {"fieldId": fields["order"], "value": online_order_id or order_id},
    ]
    return {
        "uid": "",
        "coid": "",
        "ip": "",
        "page": {},
        "data": {
            "woTypeId": workorder_type_id,
            "title": WORKORDER_TITLE,
            "beginTime": begin_time.strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "grade": DEFAULT_GRADE,
            "businessField": business_fields,
            "dingDingMsg": False,
            "woSource": DEFAULT_WORKORDER_SOURCE,
            "orderIds": [internal_order_id],
            "openUserId": "",
            "paymentType": None,
            "expressInterceptType": None,
            "remarkSoId": None,
        },
    }


def _load_template() -> dict[str, Any]:
    path = _template_path()
    if not path.exists():
        raise RuntimeError(f"未找到发票工单模板：{path}。请先运行 `ops jst order invoice learn`。")
    return _read_json(path)


def _write_template(scene_data: dict[str, Any] | None = None) -> Path:
    template = {
        "site": JST_SITE,
        "scene": JST_ORDER_INVOICE_SCENE,
        "capture_source": "sessionhub_9222",
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "endpoint": BATCH_INSERT_URL,
        "method": "POST",
        "workorder_type_id": DEFAULT_WORKORDER_TYPE_ID,
        "workorder_title": WORKORDER_TITLE,
        "field_map": DEFAULT_FIELD_MAP,
        "defaults": {
            "invoice_type": DEFAULT_INVOICE_TYPE,
            "quantity": DEFAULT_QUANTITY,
            "order_lookup_scenes": [JST_ORDER_SCENE],
            "order_lookup_keys": [OUTER_ORDER_FILTER_KEY, *ORDER_ID_FILTER_KEYS],
        },
        "captured_request": {
            "url": (scene_data or {}).get("url"),
            "method": (scene_data or {}).get("method"),
            "post_data_json": (scene_data or {}).get("post_data_json"),
        },
        "notes": [
            "首次真实创建前，建议通过 learn 捕获一次聚水潭发票工单请求，并用真实 fieldId 覆盖 field_map。",
            "Cookie、Authorization、Token 不写入代码；运行时从 SessionHub 获取。",
        ],
    }
    path = _template_path()
    _write_json(path, template)
    return path


def learn_order_invoice_workorder(*, force: bool = False) -> CommandResponse:
    manager = get_scene_manager()
    manager.ensure_scene(JST_SITE, JST_ORDER_SCENE)
    scene_data: dict[str, Any] | None = None
    try:
        scene_data = manager.capture_scene(JST_SITE, JST_ORDER_INVOICE_SCENE) if force else manager.ensure_scene(JST_SITE, JST_ORDER_INVOICE_SCENE)
    except Exception as exc:
        scene_data = {"capture_status": "template_seeded_without_scene", "reason": str(exc)}
    template_path = _write_template(scene_data)
    context_path = write_runtime_context(
        task_name="jst_order_invoice_learn",
        status="success",
        inputs={"force": force},
        outputs={
            "site": JST_SITE,
            "scene": JST_ORDER_INVOICE_SCENE,
            "template_path": str(template_path),
            "scene_data_status": scene_data.get("status") if isinstance(scene_data, dict) else None,
        },
        artifacts=[str(template_path)],
    )
    return CommandResponse(
        success=True,
        platform="jst",
        command="order invoice learn",
        data={
            "site": JST_SITE,
            "scene": JST_ORDER_INVOICE_SCENE,
            "template_path": str(template_path),
            "context_path": str(context_path),
            "source": "sessionhub_9222",
            "next_command": "ops --json jst order invoice --order-id <订单号> --title <抬头> --tax-no <税号> --address <地址> --phone <电话> --bank <开户行> --bank-account <账号> --amount <金额>",
        },
    )


def _post_workorder(payload: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    session = get_scene_manager().ensure_scene(JST_SITE, JST_ORDER_SCENE)
    endpoint = str(template.get("endpoint") or template.get("url") or BATCH_INSERT_URL)
    method = str(template.get("method") or "POST").upper()
    headers = _api_headers(session, template.get("headers") if isinstance(template.get("headers"), dict) else None)
    with build_client(follow_redirects=True, timeout=60.0) as client:
        response = client.request(method, endpoint, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    if isinstance(data, dict) and data.get("success") is False:
        raise RuntimeError(f"创建发票工单失败：{data}")
    if isinstance(data, dict) and data.get("code") not in (None, 0, "0"):
        raise RuntimeError(f"创建发票工单失败：{data}")
    return data if isinstance(data, dict) else {"data": data}


def run_order_invoice_workorder(
    *,
    order_id: str,
    outer_order_id: str | None,
    invoice_type: str,
    title: str,
    tax_no: str,
    address: str,
    phone: str,
    bank: str,
    bank_account: str,
    amount: str,
    quantity: int,
    execute: bool,
) -> CommandResponse:
    if not order_id and not outer_order_id:
        raise RuntimeError("请传入 --order-id 或 --outer-order-id")
    if quantity <= 0:
        raise RuntimeError("--quantity 必须大于 0")
    _validate_required(
        title=title,
        tax_no=tax_no,
        address=address,
        phone=phone,
        bank=bank,
        bank_account=bank_account,
    )
    amount_value = _money(amount)
    lookup_id = order_id or outer_order_id or ""
    identity = _resolve_order_identity(order_id=lookup_id, outer_order_id=outer_order_id)
    template = _load_template() if execute else {}
    field_map = template.get("field_map") if isinstance(template.get("field_map"), dict) else DEFAULT_FIELD_MAP
    workorder_type_id = str(template.get("workorder_type_id") or DEFAULT_WORKORDER_TYPE_ID)
    payload = build_invoice_workorder_payload(
        order_id=lookup_id,
        internal_order_id=identity["internal_order_id"],
        online_order_id=identity.get("online_order_id") or "",
        invoice_type=invoice_type or DEFAULT_INVOICE_TYPE,
        title=title,
        tax_no=tax_no,
        address=address,
        phone=phone,
        bank=bank,
        bank_account=bank_account,
        amount=amount_value,
        quantity=quantity,
        field_map=field_map,
        workorder_type_id=workorder_type_id,
    )
    result: dict[str, Any] | None = None
    if execute:
        result = _post_workorder(payload, template)
    outputs = {
        "order_id": lookup_id,
        "outer_order_id": outer_order_id,
        "matched_filter": identity.get("matched_filter"),
        "internal_order_id": identity["internal_order_id"],
        "online_order_id": identity.get("online_order_id"),
        "invoice_type": invoice_type or DEFAULT_INVOICE_TYPE,
        "title": title,
        "tax_no": tax_no,
        "amount": float(amount_value),
        "quantity": quantity,
        "submitted": execute,
        "mode": "execute" if execute else "dry-run",
        "scene": JST_ORDER_INVOICE_SCENE,
        "payload": payload,
        "result": result or {},
    }
    context_path = write_runtime_context(
        task_name="jst_order_invoice_run",
        status="success",
        inputs={
            "order_id": order_id,
            "outer_order_id": outer_order_id,
            "invoice_type": invoice_type,
            "title": title,
            "tax_no": tax_no,
            "amount": amount,
            "quantity": quantity,
            "execute": execute,
        },
        outputs=outputs,
    )
    return CommandResponse(
        success=True,
        platform="jst",
        command="order invoice",
        data={**outputs, "context_path": str(context_path)},
    )
