#!/usr/bin/env python3
"""Process Tmall supermarket bill files from Downloads into the maintained archive."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config_loader import get_path  # noqa: E402

DEFAULT_WORK_DIR = get_path("maochao_work_dir")
DEFAULT_BILL_DIR = get_path("tmall_bill_download_dir")
DEFAULT_STATEMENT_LIST = get_path("tmall_statement_list_file")
INTERNAL_SOURCE_SCRIPT = Path(__file__).resolve().with_name("processor.py")
INTERNAL_DOWNLOADER_SCRIPT = Path(__file__).resolve().with_name("downloader.py")
EXTERNAL_SOURCE_SCRIPT = DEFAULT_WORK_DIR / "项目资料" / "脚本" / "process_maochao_bills.py"
DEFAULT_SCRIPT_DIR = DEFAULT_WORK_DIR / "项目资料" / "脚本"
DEFAULT_TABLE1_FILE = get_path("tmall_goods_master_file")
DEFAULT_TABLE2_FILE = get_path("jst_product_master_file")
SYSTEM_PYTHON = Path("/usr/bin/python3")
SESSIONHUB_RECOVERY_TEXT = """请运行：
cd /Users/dasheng/Desktop/电商Brain/02-运营店铺/Ops-Cli/sessionhub
python3 sessionhub.py chrome start
python3 sessionhub.py capture tmall_chaoshi --scene download_file_query
python3 sessionhub.py capture tmall_chaoshi --scene statement_bill_dynamic_list"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从下载目录读取 HDB 账单并整理归档到猫超月账单数据")
    parser.add_argument("--bill-dir", default=str(DEFAULT_BILL_DIR), help="HDB*.xlsx 所在目录")
    parser.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR), help="商品表、聚水潭资料和归档目录所在工作区")
    parser.add_argument("--source-script", default=str(INTERNAL_SOURCE_SCRIPT), help="猫超账单整理脚本路径；默认使用当前项目内部实现")
    parser.add_argument("--statement-list", default=str(DEFAULT_STATEMENT_LIST), help="对账单列表文件路径")
    parser.add_argument("--table1-file", default=str(DEFAULT_TABLE1_FILE), help="猫超商品列表主表路径；也兼容传文件名")
    parser.add_argument("--table2-file", default=str(DEFAULT_TABLE2_FILE), help="聚水潭商品资料路径；也兼容传文件名")
    parser.add_argument("--downloader-script", default=str(INTERNAL_DOWNLOADER_SCRIPT), help="没有 HDB 数据源时自动调用的猫超账单下载脚本；默认使用当前项目内部实现")
    parser.add_argument("--skip-auto-download", action="store_true", help="没有 HDB 数据源时不自动下载")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不生成文件、不移动 HDB")
    return parser.parse_args()


def find_hdb_files(bill_dir: Path) -> list[Path]:
    return sorted(path for path in bill_dir.glob("HDB*.xlsx") if path.is_file())


def choose_downloader_python() -> str:
    if SYSTEM_PYTHON.exists():
        return str(SYSTEM_PYTHON)
    return sys.executable


def resolve_configured_file(value: str, base_dir: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (base_dir / path).resolve()


def auto_download_bills_if_needed(args: argparse.Namespace, bill_dir: Path) -> dict:
    existing = find_hdb_files(bill_dir)
    if existing:
        return {
            "auto_download_attempted": False,
            "auto_download_reason": "downloads_has_hdb",
            "existing_bill_count": len(existing),
        }

    if args.skip_auto_download:
        raise SystemExit(f"未在 {bill_dir} 找到 HDB*.xlsx，且已设置 --skip-auto-download")
    if args.dry_run:
        raise SystemExit(f"未在 {bill_dir} 找到 HDB*.xlsx。dry-run 不会自动下载账单，请先放入数据源或去掉 --dry-run。")

    downloader_script = Path(args.downloader_script).expanduser().resolve()
    if not downloader_script.exists():
        raise SystemExit(f"未找到猫超账单下载脚本：{downloader_script}")

    command = [
        choose_downloader_python(),
        str(downloader_script),
        "--last-month",
        "--output-dir",
        str(bill_dir),
    ]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(
            "未找到 HDB 数据源，自动下载也失败。\n"
            f"处理方式：要么自行下载 HDB*.xlsx 放到 {bill_dir}；"
            "要么刷新 SessionHub 动态 session。\n\n"
            f"{SESSIONHUB_RECOVERY_TEXT}\n\n"
            f"自动下载命令：{' '.join(command)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    downloaded = find_hdb_files(bill_dir)
    if not downloaded:
        raise SystemExit(
            f"自动下载命令执行成功，但 {bill_dir} 下仍未找到 HDB*.xlsx。"
            "请检查猫超后台是否有账单、下载脚本输出目录是否正确。"
        )

    return {
        "auto_download_attempted": True,
        "auto_download_returncode": result.returncode,
        "auto_download_stdout": result.stdout,
        "auto_download_stderr": result.stderr,
        "bill_count_after_download": len(downloaded),
    }


def load_source_module(script_path: Path):
    if not script_path.is_file():
        raise SystemExit(f"未找到原账单整理脚本：{script_path}")
    spec = importlib.util.spec_from_file_location("maochao_bills_source", script_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载原账单整理脚本：{script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def to_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def infer_bill_year_month(bill_files: list[Path]) -> tuple[int | None, int | None]:
    for path in bill_files:
        name = path.name
        if name.startswith("HDB") and len(name) >= 9:
            try:
                return int(name[3:7]), int(name[7:9])
            except ValueError:
                continue
    return None, None


def format_hdb_period(start: str, end: str) -> str:
    return f"{start[:4]}-{start[4:6]}-{start[6:8]}~{end[:4]}-{end[4:6]}-{end[6:8]}"


def infer_bill_periods(bill_files: list[Path]) -> list[str]:
    periods: list[str] = []
    for path in bill_files:
        name = path.name
        if not name.startswith("HDB") or len(name) < 19:
            continue
        start = name[3:11]
        end = name[11:19]
        if not (start.isdigit() and end.isdigit()):
            continue
        periods.append(format_hdb_period(start, end))
    return periods


def infer_bill_date_range(bill_files: list[Path]) -> tuple[str, str]:
    starts: list[str] = []
    ends: list[str] = []
    for path in bill_files:
        name = path.name
        if not name.startswith("HDB") or len(name) < 19:
            continue
        start = name[3:11]
        end = name[11:19]
        if start.isdigit() and end.isdigit():
            starts.append(f"{start[:4]}-{start[4:6]}-{start[6:8]}")
            ends.append(f"{end[:4]}-{end[4:6]}-{end[6:8]}")
    if not starts or not ends:
        raise SystemExit("无法从 HDB 文件名解析账单日期，无法自动下载对账单列表")
    return min(starts), max(ends)


def statement_list_candidates(statement_path: Path) -> list[Path]:
    parent = statement_path.parent
    stem = statement_path.stem
    suffix = statement_path.suffix
    patterns = [
        f"{stem}{suffix}",
        f"{stem}(*){suffix}",
        f"{stem} (*){suffix}",
    ]
    candidates: dict[Path, None] = {}
    for pattern in patterns:
        for path in parent.glob(pattern):
            if path.is_file() and not path.name.startswith("~$"):
                candidates[path.resolve()] = None
    return sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)


def normalize_period(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def sum_column(rows: list[list[object]], header: list[str], column_name: str) -> Decimal:
    try:
        index = header.index(column_name)
    except ValueError as exc:
        raise SystemExit(f"未找到字段：{column_name}") from exc
    total = Decimal("0")
    for row in rows:
        if index >= len(row):
            continue
        amount = to_decimal(row[index])
        if amount is not None:
            total += amount
    return total


def load_statement_rows(source, statement_path: Path) -> tuple[list[str], list[list[object]]]:
    if not statement_path.exists():
        raise SystemExit(f"未找到对账单列表：{statement_path}")
    workbook = source.load_workbook(statement_path, read_only=True, data_only=True)
    worksheet = workbook[workbook.sheetnames[0]]
    # Some exports write an incorrect <dimension ref="A1"/>; reset so openpyxl streams all cells.
    if hasattr(worksheet, "reset_dimensions"):
        worksheet.reset_dimensions()
    iterator = worksheet.iter_rows(values_only=True)
    try:
        header_row = next(iterator)
    except StopIteration as exc:
        raise SystemExit(f"对账单列表为空：{statement_path}") from exc
    header = [str(value).strip() if value is not None else "" for value in header_row]
    rows = [list(row) for row in iterator if any(value not in (None, "") for value in row)]
    return header, rows


def statement_matches_periods(source, statement_path: Path, bill_period_set: set[str]) -> bool:
    statement_header, statement_rows = load_statement_rows(source, statement_path)
    try:
        period_index = statement_header.index("账单周期")
    except ValueError:
        return False
    return any(
        normalize_period(row[period_index] if period_index < len(row) else None) in bill_period_set
        for row in statement_rows
    )


def resolve_statement_list(source, statement_path: Path, bill_periods: list[str]) -> Path:
    bill_period_set = set(bill_periods)
    candidates = statement_list_candidates(statement_path)
    if not candidates:
        raise SystemExit(
            "未找到对账单列表：\n"
            f"{statement_path}\n"
            "也未找到同名重名文件，例如 对账单列表(1).xlsx。\n"
            "请先从猫超后台导出对账单列表，或去掉 --dry-run 让脚本通过 SessionHub 自动导出。"
        )

    for candidate in candidates:
        if statement_matches_periods(source, candidate, bill_period_set):
            if candidate != statement_path:
                print(f"已使用最新匹配对账单列表：{candidate}", flush=True)
            return candidate

    candidate_text = "\n".join(f"- {path}" for path in candidates[:5])
    raise SystemExit(
        "已找到对账单列表文件，但没有匹配当前 HDB 账单周期的数据。\n"
        f"当前 HDB 账期：{', '.join(bill_periods)}\n"
        f"检查过的文件：\n{candidate_text}\n"
        "请下载包含对应月份/账期的最新对账单列表，或去掉 --dry-run 让脚本通过 SessionHub 自动导出。"
    )


def find_matching_statement_list(source, statement_path: Path, bill_periods: list[str]) -> Path | None:
    bill_period_set = set(bill_periods)
    for candidate in statement_list_candidates(statement_path):
        if statement_matches_periods(source, candidate, bill_period_set):
            return candidate
    return None


def auto_download_statement_list_if_needed(
    args: argparse.Namespace,
    source,
    statement_path: Path,
    bill_files: list[Path],
    bill_dir: Path,
) -> dict:
    bill_periods = infer_bill_periods(bill_files)
    existing = find_matching_statement_list(source, statement_path, bill_periods)
    if existing:
        return {
            "statement_auto_download_attempted": False,
            "statement_auto_download_reason": "matching_statement_list_exists",
            "statement_list_before_process": str(existing),
        }

    if args.skip_auto_download:
        raise SystemExit("未找到匹配当前 HDB 账期的对账单列表，且已设置 --skip-auto-download")
    if args.dry_run:
        raise SystemExit("未找到匹配当前 HDB 账期的对账单列表。dry-run 不会自动下载，请先下载对账单列表或去掉 --dry-run。")

    downloader_script = Path(args.downloader_script).expanduser().resolve()
    start, end = infer_bill_date_range(bill_files)
    command = [
        choose_downloader_python(),
        str(downloader_script),
        "--start",
        start,
        "--end",
        end,
        "--output-dir",
        str(bill_dir),
        "--download-statement-list",
    ]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(
            "未找到匹配当前 HDB 账期的对账单列表，自动导出也失败。\n"
            "处理方式：登录猫超后台确认对账单列表页面正常，并刷新 SessionHub 动态 session。\n\n"
            f"{SESSIONHUB_RECOVERY_TEXT}\n\n"
            f"自动导出命令：{' '.join(command)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    downloaded = find_matching_statement_list(source, statement_path, bill_periods)
    if not downloaded:
        raise SystemExit(
            "已执行对账单列表自动导出，但下载目录里仍未找到匹配当前 HDB 账期的对账单列表。"
            "请检查导出的列表是否包含对应账单周期。"
        )

    return {
        "statement_auto_download_attempted": True,
        "statement_auto_download_returncode": result.returncode,
        "statement_auto_download_stdout": result.stdout,
        "statement_auto_download_stderr": result.stderr,
        "statement_list_before_process": str(downloaded),
    }


def unique_archive_target(archive_dir: Path, source_path: Path) -> Path:
    target = archive_dir / source_path.name
    if not target.exists():
        return target
    stem = source_path.stem
    suffix = source_path.suffix
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = archive_dir / f"{stem}-{stamp}{suffix}"
    counter = 1
    while candidate.exists():
        candidate = archive_dir / f"{stem}-{stamp}-{counter}{suffix}"
        counter += 1
    return candidate


def archive_statement_list(statement_path: Path, archive_dir: Path) -> Path:
    target = unique_archive_target(archive_dir, statement_path)
    shutil.move(str(statement_path), str(target))
    return target


def compare_invoice_amount(source, statement_path: Path, invoice_header: list[str], invoice_rows: list[list[object]], bill_files: list[Path]) -> dict:
    year, month = infer_bill_year_month(bill_files)
    bill_periods = infer_bill_periods(bill_files)
    bill_period_set = set(bill_periods)
    if not bill_period_set:
        raise SystemExit("无法从 HDB 文件名解析账单周期，无法校验开票金额")
    invoice_sum = sum_column(invoice_rows, invoice_header, "开票金额")

    statement_path = resolve_statement_list(source, statement_path, bill_periods)
    statement_header, statement_rows = load_statement_rows(source, statement_path)
    try:
        period_index = statement_header.index("账单周期")
    except ValueError as exc:
        raise SystemExit("对账单列表未找到字段：账单周期") from exc
    try:
        amount_index = statement_header.index("商家开票含税总额")
    except ValueError as exc:
        raise SystemExit("对账单列表未找到字段：商家开票含税总额") from exc

    statement_sum = Decimal("0")
    matched_periods: list[str] = []
    for row in statement_rows:
        period = row[period_index] if period_index < len(row) else None
        normalized_period = normalize_period(period)
        if normalized_period not in bill_period_set:
            continue
        matched_periods.append(normalized_period)
        amount = to_decimal(row[amount_index] if amount_index < len(row) else None)
        if amount is not None:
            statement_sum += amount

    invoice_compare_amount = int(invoice_sum)
    statement_compare_amount = int(statement_sum)
    result = "开票金额正确" if invoice_compare_amount == statement_compare_amount else "开票金额不正确"

    return {
        "statement_list": str(statement_path),
        "bill_year": year,
        "bill_month": month,
        "bill_periods": bill_periods,
        "matched_statement_periods": matched_periods,
        "invoice_amount_sum": str(invoice_sum),
        "statement_invoice_tax_total_sum": str(statement_sum),
        "invoice_compare_amount": invoice_compare_amount,
        "statement_compare_amount": statement_compare_amount,
        "invoice_amount_check": result,
    }


def process(args: argparse.Namespace) -> dict:
    bill_dir = Path(args.bill_dir).expanduser().resolve()
    work_dir = Path(args.work_dir).expanduser().resolve()
    source_script = Path(args.source_script).expanduser().resolve()
    statement_path = Path(args.statement_list).expanduser().resolve()

    if not bill_dir.is_dir():
        raise SystemExit(f"HDB 账单目录不存在：{bill_dir}")
    if not work_dir.is_dir():
        raise SystemExit(f"工作区不存在：{work_dir}")

    auto_download_info = auto_download_bills_if_needed(args, bill_dir)
    source = load_source_module(source_script)

    bill_files = source.get_bill_files(bill_dir)
    statement_download_info = auto_download_statement_list_if_needed(args, source, statement_path, bill_files, bill_dir)
    table1_path = resolve_configured_file(args.table1_file, work_dir)
    table2_path = resolve_configured_file(args.table2_file, work_dir)
    if not table1_path.exists():
        raise SystemExit(f"未找到猫超商品列表主表：{table1_path}")
    if not table2_path.exists():
        raise SystemExit(f"未找到聚水潭商品资料：{table2_path}")

    month = source.infer_month_from_bills(bill_files)
    main_sheet_name = source.MAIN_SHEET_TEMPLATE.format(month=month)
    archive_dir = work_dir / source.ARCHIVE_ROOT_NAME / source.ARCHIVE_SUBDIR_TEMPLATE.format(month=month)
    output_path = archive_dir / source.OUTPUT_TEMPLATE.format(month=month)
    stale_output_path = work_dir / output_path.name

    raw_header, raw_rows = source.build_combined_rows(bill_files)
    table1_mapping = source.build_table1_mapping(table1_path)
    table2_mapping = source.build_table2_mapping(table2_path)
    enriched_header, enriched_rows, stats = source.enrich_rows(raw_header, raw_rows, table1_mapping, table2_mapping)

    main_rows_sorted = source.sort_rows_by_backend_code(raw_header, raw_rows)
    cargo_rows = source.build_sub_sheet_rows(enriched_header, enriched_rows, "货款表格")
    ticket_rows = source.build_sub_sheet_rows(enriched_header, enriched_rows, "票扣表格")
    charge_rows = source.build_sub_sheet_rows(raw_header, raw_rows, "账扣表格")
    invoice_header, invoice_rows, price_conflict_codes = source.build_invoice_sheet(
        enriched_header,
        cargo_rows,
        enriched_header,
        ticket_rows,
    )
    cost_header, cost_rows = source.build_cost_sheet(enriched_header, cargo_rows)
    invoice_check = compare_invoice_amount(source, statement_path, invoice_header, invoice_rows, bill_files)
    statement_archive_path = None

    if not args.dry_run:
        archive_dir.mkdir(parents=True, exist_ok=True)
        source.ensure_clean_target(output_path)
        if stale_output_path != output_path and stale_output_path.exists():
            source.ensure_clean_target(stale_output_path)

        workbook = source.Workbook()
        workbook.remove(workbook.active)
        source.append_sheet(workbook, main_sheet_name, raw_header, main_rows_sorted)
        source.append_sheet(workbook, "货款表格", enriched_header, cargo_rows)
        source.append_sheet(workbook, "票扣表格", enriched_header, ticket_rows)
        source.append_sheet(workbook, "账扣表格", raw_header, charge_rows)
        source.append_sheet(workbook, "开票表", invoice_header, invoice_rows)
        source.append_sheet(workbook, "成本表", cost_header, cost_rows)
        workbook.save(output_path)
        source.archive_bill_files(bill_files, archive_dir)
        statement_archive_path = archive_statement_list(Path(invoice_check["statement_list"]), archive_dir)

    return {
        "task": "process_maochao_bills",
        "dry_run": args.dry_run,
        "bill_dir": str(bill_dir),
        "work_dir": str(work_dir),
        "source_script": str(source_script),
        "output_file": str(output_path),
        "archive_dir": str(archive_dir),
        "bill_file_count": len(bill_files),
        "bill_files": [str(path) for path in bill_files],
        "bill_files_moved": not args.dry_run,
        **statement_download_info,
        "statement_list_moved": bool(statement_archive_path),
        "statement_list_archive_path": str(statement_archive_path) if statement_archive_path else None,
        **auto_download_info,
        "main_sheet": main_sheet_name,
        "total_rows": len(raw_rows),
        "mapped_table1": stats["mapped_table1"],
        "unmatched_table1": stats["unmatched_table1"],
        "mapped_table2": stats["mapped_table2"],
        "unmatched_table2": stats["unmatched_table2"],
        "cargo_rows": len(cargo_rows),
        "ticket_rows": len(ticket_rows),
        "charge_rows": len(charge_rows),
        "invoice_rows": len(invoice_rows),
        "cost_rows": len(cost_rows),
        "price_conflict_codes": price_conflict_codes,
        **invoice_check,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }


def main() -> int:
    payload = process(parse_args())
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
