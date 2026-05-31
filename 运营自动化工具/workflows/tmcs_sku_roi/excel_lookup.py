from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook


TMCS_REQUIRED_HEADERS = ("商品编码", "SKU编码", "条码")
JST_REQUIRED_HEADERS = ("商品编码", "淘系控价", "成本价")


def _normalize_header(value) -> str:
    return str(value or "").strip()


def _load_sheet(path: Path):
    workbook = load_workbook(path, read_only=True, data_only=False)
    return workbook, workbook[workbook.sheetnames[0]]


def _header_map(sheet) -> dict[str, int]:
    headers = {}
    header_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
    for column, raw_value in enumerate(header_row, start=1):
        header = _normalize_header(raw_value)
        if header:
            headers[header] = column
    return headers


def _require_headers(headers: dict[str, int], required: tuple[str, ...], file_label: str) -> None:
    missing = [name for name in required if name not in headers]
    if missing:
        raise ValueError(f"{file_label} 缺少字段：{', '.join(missing)}")


def find_tmcs_barcode(path: Path, *, sku_code: str | None = None, product_code: str | None = None) -> dict[str, str]:
    workbook, sheet = _load_sheet(path)
    try:
        headers = _header_map(sheet)
        _require_headers(headers, TMCS_REQUIRED_HEADERS, "猫超商品列表")
        product_index = headers["商品编码"] - 1
        sku_index = headers["SKU编码"] - 1
        barcode_index = headers["条码"] - 1
        if sku_code:
            mode = "sku_code"
            lookup_value = sku_code
        elif product_code:
            mode = "product_code"
            lookup_value = product_code
        else:
            raise ValueError("缺少猫超查询键：sku_code 或 product_code")

        first_match_barcode = None
        for row_values in sheet.iter_rows(min_row=2, values_only=True):
            if mode == "sku_code":
                value = _normalize_header(row_values[sku_index] if sku_index < len(row_values) else None)
            else:
                value = _normalize_header(row_values[product_index] if product_index < len(row_values) else None)
            if value != lookup_value:
                continue
            barcode = _normalize_header(row_values[barcode_index] if barcode_index < len(row_values) else None)
            if not barcode:
                raise ValueError(f"{'SKU' if mode == 'sku_code' else '商品编码'} {lookup_value} 已找到，但条码为空")
            if mode == "sku_code":
                return {"sku_code": lookup_value, "barcode": barcode}
            if first_match_barcode is None:
                first_match_barcode = barcode
        if first_match_barcode is not None:
            return {"product_code": lookup_value, "barcode": first_match_barcode}
    finally:
        workbook.close()
    if sku_code:
        raise ValueError(f"猫超商品列表未找到 SKU 编码：{sku_code}")
    raise ValueError(f"猫超商品列表未找到 商品编码：{product_code}")


def _parse_control_price(raw_value) -> float:
    text = str(raw_value or "").strip()
    if not text:
        raise ValueError("聚水潭商品资料中的淘系控价为空")
    parts = [part for part in text.replace("\n", " ").split() if part]
    if len(parts) > 1:
        raise ValueError(f"聚水潭商品资料中的淘系控价存在多个值：{text}")
    try:
        return float(parts[0])
    except ValueError as exc:
        raise ValueError(f"聚水潭商品资料中的淘系控价不是有效数字：{text}") from exc


def find_jst_product(path: Path, barcode_as_product_code: str) -> dict[str, float | str]:
    workbook, sheet = _load_sheet(path)
    try:
        headers = _header_map(sheet)
        _require_headers(headers, JST_REQUIRED_HEADERS, "聚水潭商品资料")
        code_index = headers["商品编码"] - 1
        price_index = headers["淘系控价"] - 1
        cost_index = headers["成本价"] - 1
        matches = []
        for row_values in sheet.iter_rows(min_row=2, values_only=True):
            code = _normalize_header(row_values[code_index] if code_index < len(row_values) else None)
            if code != barcode_as_product_code:
                continue
            raw_cost = row_values[cost_index] if cost_index < len(row_values) else None
            matches.append(
                {
                    "product_code": code,
                    "price": _parse_control_price(row_values[price_index] if price_index < len(row_values) else None),
                    "cost": float(raw_cost),
                }
            )
    finally:
        workbook.close()

    if not matches:
        raise ValueError(f"聚水潭商品资料未找到商品编码：{barcode_as_product_code}")
    if len(matches) > 1:
        raise ValueError(f"聚水潭商品资料中商品编码重复：{barcode_as_product_code}")
    match = matches[0]
    if match["cost"] <= 0:
        raise ValueError(f"聚水潭商品资料中的成本价无效：{match['cost']}")
    return match


def write_result_json(path: Path, payload: dict) -> Path:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_result_excel(path: Path, payload: dict) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "ROI结果"
    sheet.append(["字段", "值"])
    for key in ("保本ROI", "安全ROI", "理想ROI"):
        sheet.append([key, payload[key]])
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    workbook.close()
    return path
