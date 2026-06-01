from __future__ import annotations

from pathlib import Path

from core.task_registry import (
    TASKS,
    TASK_ALIASES,
    FUZZY_TASK_RULES,
    _parse_task_yaml,
    normalize_task_text,
    resolve_task,
    task_required_modules,
    task_scripts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# --- _parse_task_yaml tests ---


def test_parse_task_yaml_flat_key_value(tmp_path: Path) -> None:
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("name: buyer_show\ndescription: 买家秀\n", encoding="utf-8")
    result = _parse_task_yaml(yaml_file)
    assert result["name"] == "buyer_show"
    assert result["description"] == "买家秀"


def test_parse_task_yaml_list_items(tmp_path: Path) -> None:
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        "aliases:\n  - buyer_show\n  - 买家秀自动化\n",
        encoding="utf-8",
    )
    result = _parse_task_yaml(yaml_file)
    assert result["aliases"] == ["buyer_show", "买家秀自动化"]


def test_parse_task_yaml_inline_list(tmp_path: Path) -> None:
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        "fuzzy_keywords:\n  - [猫超, 账单]\n  - [月账单]\n",
        encoding="utf-8",
    )
    result = _parse_task_yaml(yaml_file)
    assert result["fuzzy_keywords"] == [("猫超", "账单"), ("月账单",)]


def test_parse_task_yaml_empty_inline_list(tmp_path: Path) -> None:
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("required_modules: []\n", encoding="utf-8")
    result = _parse_task_yaml(yaml_file)
    assert result["required_modules"] == []


def test_parse_task_yaml_ignores_comments_and_blanks(tmp_path: Path) -> None:
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        "# comment\n\nname: test\n  # indented comment\n",
        encoding="utf-8",
    )
    result = _parse_task_yaml(yaml_file)
    assert result == {"name": "test"}


# --- _discover_tasks integration tests ---


def test_discover_tasks_returns_all_registered_tasks() -> None:
    expected = {
        "buyer_show",
        "append_brush_orders",
        "tag_jst_brush_orders",
        "jst_brush_reimburse_workorder",
        "company_nas_listing",
        "company_nas_index",
        "process_maochao_bills",
        "update_jst_products",
        "update_maochao_goods",
        "tmcs_sku_roi",
        "tmcs_sync_jst_shop_goods",
        "jst_pickup_watch",
        "retry_queue",
        "jst_order_invoice_workorder",
        "tmcs_xp_workorder_watch",
    }
    assert set(TASKS.keys()) == expected


def test_discover_tasks_aliases_populated() -> None:
    assert "买家秀自动化" in TASK_ALIASES
    assert TASK_ALIASES["买家秀自动化"] == "buyer_show"
    assert "刷单表格登记" in TASK_ALIASES
    assert TASK_ALIASES["刷单表格登记"] == "append_brush_orders"


def test_discover_tasks_fuzzy_rules_populated() -> None:
    assert len(FUZZY_TASK_RULES) == 15
    rule_names = {name for name, _ in FUZZY_TASK_RULES}
    assert "buyer_show" in rule_names
    assert "retry_queue" in rule_names
    assert "tmcs_sku_roi" in rule_names


# --- resolve_task tests ---


def test_resolve_task_exact_name() -> None:
    assert resolve_task("buyer_show") == "buyer_show"
    assert resolve_task("retry_queue") == "retry_queue"


def test_resolve_task_alias() -> None:
    assert resolve_task("买家秀自动化") == "buyer_show"
    assert resolve_task("刷单表格登记") == "append_brush_orders"
    assert resolve_task("聚水潭刷单订单打标") == "tag_jst_brush_orders"


def test_resolve_task_fuzzy() -> None:
    assert resolve_task("刷单登记") == "append_brush_orders"
    assert resolve_task("猫超账单") == "process_maochao_bills"
    assert resolve_task("聚水潭揽收监控") == "jst_pickup_watch"


def test_resolve_task_unknown_raises() -> None:
    try:
        resolve_task("不存在的任务")
    except SystemExit as exc:
        assert "不存在的任务" in str(exc) or "未知任务" in str(exc)
    else:
        raise AssertionError("Expected SystemExit for unknown task")


# --- normalize_task_text ---


def test_normalize_task_text_fixes_typo() -> None:
    assert normalize_task_text("剧水潭") == "聚水潭"


# --- task_scripts ---


def test_task_scripts_returns_paths() -> None:
    scripts = task_scripts()
    assert len(scripts) == 15
    assert scripts["buyer_show"] == PROJECT_ROOT / "tasks" / "buyer_show.py"
    assert scripts["tag_jst_brush_orders"] == PROJECT_ROOT / "tasks" / "jst_order_label" / "main.py"
    assert scripts["tmcs_sku_roi"] == PROJECT_ROOT / "tasks" / "tmcs_sku_roi" / "main.py"


# --- task_required_modules ---


def test_task_required_modules_buyer_show() -> None:
    modules = task_required_modules()
    assert modules["buyer_show"] == ("openpyxl", "PIL")


def test_task_required_modules_empty_for_tag_jst() -> None:
    modules = task_required_modules()
    assert modules["tag_jst_brush_orders"] == ()


def test_task_required_modules_jst_brush_reimburse() -> None:
    modules = task_required_modules()
    assert modules["jst_brush_reimburse_workorder"] == ("requests", "openpyxl")
