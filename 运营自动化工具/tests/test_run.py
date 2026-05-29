from __future__ import annotations

import sys
from pathlib import Path

from run import choose_python, python_candidates, python_has_modules


def test_python_candidates_starts_with_sys_executable() -> None:
    candidates = python_candidates()
    assert candidates[0] == Path(sys.executable)


def test_python_candidates_no_duplicates() -> None:
    candidates = python_candidates()
    assert len(candidates) == len(set(str(c) for c in candidates))


def test_python_has_modules_returns_false_for_missing() -> None:
    assert python_has_modules(Path("/nonexistent/python3"), ("nonexistent_module_xyz",)) is False


def test_choose_python_returns_sys_executable_fallback(monkeypatch) -> None:
    monkeypatch.setattr("run.python_candidates", lambda: [])
    result = choose_python("tag_jst_brush_orders")
    assert result == sys.executable


def test_task_required_modules_matches_expected() -> None:
    from core.task_registry import task_required_modules

    modules = task_required_modules()
    assert modules["buyer_show"] == ("openpyxl", "PIL")
    assert modules["tag_jst_brush_orders"] == ()
    assert modules["jst_brush_reimburse_workorder"] == ("requests", "openpyxl")
    assert modules["process_maochao_bills"] == ("openpyxl",)
