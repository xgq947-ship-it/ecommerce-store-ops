from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Paths derived from project structure — always available without config
DEFAULT_PATHS = {
    "project_root": PROJECT_ROOT,
    "runtime_dir": PROJECT_ROOT / "runtime",
    "logs_dir": PROJECT_ROOT / "logs",
    "pickup_watch_config": PROJECT_ROOT / "config" / "pickup_watch.json",
    "ops_cli_root": PROJECT_ROOT.parent / "Ops-Cli",
    "ops_cli_bin": PROJECT_ROOT.parent / "Ops-Cli" / ".venv" / "bin" / "ops",
    "nas_index_dir": PROJECT_ROOT / "runtime" / "nas_index",
    "nas_index_json": PROJECT_ROOT / "runtime" / "nas_index" / "company_nas_tree.json",
    "nas_index_md": PROJECT_ROOT / "runtime" / "nas_index" / "company_nas_tree.md",
    "nas_index_csv": PROJECT_ROOT / "runtime" / "nas_index" / "company_nas_files.csv",
    "brush_register_pattern": Path("天猫超市*月刷单登记明细.xlsx"),
}

# Paths that must be configured in config/paths.yaml
_PERSONAL_PATHS = {
    "desktop_dir",
    "downloads_dir",
    "ecommerce_brain_dir",
    "product_library_dir",
    "reimbursement_dir",
    "brush_register_dir",
    "backup_dir",
    "brush_orders_dir",
    "brush_product_file",
    "wechat_file_dir",
    "jst_product_file",
    "jst_product_master_file",
    "jst_product_import_file",
    "maochao_goods_master_file",
    "tmall_goods_master_file",
    "maochao_monthly_bill_dir",
    "maochao_work_dir",
    "tmall_bill_download_dir",
    "tmall_hdb_glob",
    "tmall_statement_list_file",
    "tmall_goods_import_file",
    "buyer_show_output_dir",
    "company_nas_mount",
    "company_nas_product_root",
    "nas_product_library_dir",
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
        if name in _PERSONAL_PATHS:
            raise KeyError(
                f"路径配置缺失：{name}\n"
                f"请在 config/paths.yaml 中配置该路径。参考 config/paths.yaml.example"
            )
        raise KeyError(f"未知路径配置：{name}")
    return paths[name]
