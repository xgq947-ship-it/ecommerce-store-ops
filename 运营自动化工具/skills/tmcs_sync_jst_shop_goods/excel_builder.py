from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook


IMPORT_HEADERS = [
    "线上款式编码",
    "线上商品编码",
    "线上国标码",
    "平台店铺款式编码",
    "平台店铺商品编码",
    "原始商品编码",
    "线上商品名称",
    "线上颜色规格",
    "商品标识",
]

FAILED_HEADERS = ["platform_item_id", "platform_sku_id", "supplier_goods_id", "merchant_goods_code", "reason"]


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def build_rows(*, requested_item_ids: list[str], stock_rows: list[dict[str, Any]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    import_rows: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    returned_items: set[str] = set()

    for row in stock_rows:
        platform_item_id = _text(row.get("platform_item_id"))
        platform_sku_id = _text(row.get("platform_sku_id"))
        supplier_goods_id = _text(row.get("supplier_goods_id"))
        merchant_goods_code = _text(row.get("merchant_goods_code"))
        if platform_item_id:
            returned_items.add(platform_item_id)

        reason = ""
        if not platform_item_id:
            reason = "平台商品ID为空"
        elif not supplier_goods_id:
            reason = "供应商货品ID为空"
        elif not merchant_goods_code:
            reason = "商家货品编码为空"

        if reason:
            failures.append(
                {
                    "platform_item_id": platform_item_id,
                    "platform_sku_id": platform_sku_id,
                    "supplier_goods_id": supplier_goods_id,
                    "merchant_goods_code": merchant_goods_code,
                    "reason": reason,
                }
            )
            continue

        import_rows.append(
            {
                "线上款式编码": platform_item_id,
                "线上商品编码": merchant_goods_code,
                "线上国标码": "",
                "平台店铺款式编码": platform_item_id,
                "平台店铺商品编码": supplier_goods_id,
                "原始商品编码": merchant_goods_code,
                "线上商品名称": "",
                "线上颜色规格": "",
                "商品标识": "Retail",
            }
        )

    for item_id in requested_item_ids:
        if item_id not in returned_items:
            failures.append(
                {
                    "platform_item_id": item_id,
                    "platform_sku_id": "",
                    "supplier_goods_id": "",
                    "merchant_goods_code": "",
                    "reason": "猫超未返回数据",
                }
            )

    return import_rows, failures


def _write_workbook(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "导入数据"
    worksheet.append(headers)
    for row in rows:
        worksheet.append([_text(row.get(header)) for header in headers])
    for row in worksheet.iter_rows():
        for cell in row:
            cell.number_format = "@"
            if cell.value is None:
                cell.value = ""
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def build_import_workbooks(
    *,
    import_rows: list[dict[str, str]],
    failures: list[dict[str, str]],
    output_dir: str | Path,
    timestamp: str,
) -> dict[str, str | int | None]:
    output_path = Path(output_dir)
    import_path = output_path / f"jst_shop_goods_import_{timestamp}.xlsx"
    failed_path = output_path / f"failed_items_{timestamp}.xlsx" if failures else None
    _write_workbook(import_path, IMPORT_HEADERS, import_rows)
    if failed_path:
        _write_workbook(failed_path, FAILED_HEADERS, failures)
    return {
        "import_path": str(import_path),
        "failed_path": str(failed_path) if failed_path else None,
        "import_rows": len(import_rows),
        "failed_rows": len(failures),
    }
