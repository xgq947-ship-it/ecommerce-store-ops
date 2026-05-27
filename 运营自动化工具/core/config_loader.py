from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PATHS = {
    "project_root": PROJECT_ROOT,
    "desktop_dir": Path("/Users/dasheng/Desktop"),
    "ecommerce_brain_dir": Path("/Users/dasheng/Desktop/电商Brain"),
    "product_library_dir": Path("/Users/dasheng/Desktop/电商Brain/01-产品库"),
    "reimbursement_dir": Path("/Users/dasheng/Desktop/公司费用报销"),
    "brush_register_dir": Path("/Users/dasheng/Desktop/公司费用报销"),
    "backup_dir": Path("/Users/dasheng/Desktop/公司费用报销/备份"),
    "brush_register_pattern": Path("天猫超市*月刷单登记明细.xlsx"),
    "brush_orders_dir": Path("/Users/dasheng/Desktop/公司费用报销/今日刷单表格"),
    "brush_product_file": Path("/Users/dasheng/Desktop/公司费用报销/今日刷单产品表.xlsx"),
    "wechat_file_dir": Path(
        "/Users/dasheng/Library/Containers/com.tencent.xinWeChat/Data/Documents/"
        "xwechat_files/wxid_qkre05gkwlkd21_e73b/msg/file"
    ),
    "jst_product_file": Path("/Users/dasheng/Desktop/电商Brain/02-运营店铺/主数据/聚水潭商品资料（最新）.xlsx"),
    "jst_product_master_file": Path("/Users/dasheng/Desktop/电商Brain/02-运营店铺/主数据/聚水潭商品资料（最新）.xlsx"),
    "jst_product_import_file": Path("/Users/dasheng/Downloads/聚水潭商品资料（最新）.xlsx"),
    "maochao_goods_master_file": Path(
        "/Users/dasheng/Desktop/电商Brain/02-运营店铺/主数据/猫超商品列表导出 (最新）.xlsx"
    ),
    "tmall_goods_master_file": Path(
        "/Users/dasheng/Desktop/电商Brain/02-运营店铺/主数据/猫超商品列表导出 (最新）.xlsx"
    ),
    "maochao_monthly_bill_dir": Path("/Users/dasheng/Desktop"),
    "maochao_work_dir": Path("/Users/dasheng/Desktop"),
    "downloads_dir": Path("/Users/dasheng/Downloads"),
    "tmall_bill_download_dir": Path("/Users/dasheng/Downloads"),
    "tmall_hdb_glob": Path("/Users/dasheng/Downloads/HDB*.xlsx"),
    "tmall_statement_list_file": Path("/Users/dasheng/Downloads/对账单列表.xlsx"),
    "tmall_goods_import_file": Path("/Users/dasheng/Downloads/猫超商品列表导出.xlsx"),
    "buyer_show_output_dir": Path("/Users/dasheng/Desktop"),
    "runtime_dir": PROJECT_ROOT / "runtime",
    "logs_dir": PROJECT_ROOT / "logs",
    "pickup_watch_config": PROJECT_ROOT / "config" / "pickup_watch.json",
    "ops_cli_root": PROJECT_ROOT.parent / "Ops-Cli",
    "ops_cli_bin": PROJECT_ROOT.parent / "Ops-Cli" / ".venv" / "bin" / "ops",
    "company_nas_mount": Path("/Volumes/suolong.synology.me"),
    "company_nas_product_root": Path("/Volumes/suolong.synology.me/产品资料（运营）/1.产品资料"),
    "nas_product_library_dir": Path("/Users/dasheng/Desktop/电商Brain/01-产品库"),
    "nas_index_dir": PROJECT_ROOT / "runtime" / "nas_index",
    "nas_index_json": PROJECT_ROOT / "runtime" / "nas_index" / "company_nas_tree.json",
    "nas_index_md": PROJECT_ROOT / "runtime" / "nas_index" / "company_nas_tree.md",
    "nas_index_csv": PROJECT_ROOT / "runtime" / "nas_index" / "company_nas_files.csv",
}


def _parse_simple_yaml(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and value:
            values[key] = value
    return values


def load_paths(config_path: Path | None = None) -> dict[str, Path]:
    path = config_path or PROJECT_ROOT / "config" / "paths.yaml"
    loaded: dict[str, Path] = {}
    if path.exists():
        try:
            loaded = {key: Path(value).expanduser() for key, value in _parse_simple_yaml(path).items()}
        except OSError:
            loaded = {}
    merged = {**DEFAULT_PATHS, **loaded}
    return {key: value.expanduser() for key, value in merged.items()}


def get_path(name: str) -> Path:
    paths = load_paths()
    if name not in paths:
        raise KeyError(f"未知路径配置：{name}")
    return paths[name]
