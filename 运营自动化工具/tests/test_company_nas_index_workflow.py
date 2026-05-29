from __future__ import annotations

import json
from pathlib import Path

from core.runtime import WorkflowRunner
from core.runtime.registry import discover_workflow

from workflows.company_nas_index import steps
from workflows.company_nas_index.workflow import build_workflow


def _patch_nas(monkeypatch, calls: dict, records=None):
    monkeypatch.setattr(steps.legacy, "active_nas_mount", lambda: None)
    monkeypatch.setattr(steps.legacy, "mount_nas", lambda: calls.__setitem__("mount", calls.get("mount", 0) + 1))
    monkeypatch.setattr(steps.legacy, "unmount_nas", lambda: calls.__setitem__("unmount", calls.get("unmount", 0) + 1))
    monkeypatch.setattr(steps.legacy, "nas_product_root", lambda: Path("/nas/products"))
    monkeypatch.setattr(steps.legacy, "scan_index", lambda root, **k: records if records is not None else [{"type": "dir", "brand": "奥克斯"}])
    monkeypatch.setattr(steps.legacy, "summarize", lambda recs: {"dir_count": len(recs), "file_count": 0, "brand_count": 1, "category_count": 0, "heavy_file_count": 0})
    monkeypatch.setattr(steps.legacy, "write_json", lambda *a, **k: calls.__setitem__("json", calls.get("json", 0) + 1))
    monkeypatch.setattr(steps.legacy, "write_csv", lambda *a, **k: calls.__setitem__("csv", calls.get("csv", 0) + 1))
    monkeypatch.setattr(steps.legacy, "write_md", lambda *a, **k: calls.__setitem__("md", calls.get("md", 0) + 1))


def test_workflow_registers() -> None:
    wf = discover_workflow("company_nas_index")
    assert wf.id == "company_nas_index"
    assert [s.id for s in wf.steps] == [
        "check_inputs",
        "scan_nas",
        "build_index",
        "save_index",
        "collect_artifacts",
    ]


def test_dry_run_scans_but_does_not_write_index(monkeypatch, tmp_path: Path) -> None:
    calls: dict = {}
    _patch_nas(monkeypatch, calls)

    runner = WorkflowRunner(tmp_path)
    run = runner.run(build_workflow(), inputs={"dry_run": True, "args": ["--dry-run"]}, dry_run=True)

    assert run.status == "dry_run_success"
    assert calls.get("json", 0) == 0  # 未写正式索引
    assert calls.get("csv", 0) == 0
    assert calls.get("md", 0) == 0
    assert calls.get("mount", 0) == 1
    assert calls.get("unmount", 0) == 1  # 收尾卸载
    save_step = json.loads((runner.last_run_dir / "steps" / "save_index.json").read_text(encoding="utf-8"))
    assert save_step["outputs"]["skipped"] is True


def test_real_run_writes_index(monkeypatch, tmp_path: Path) -> None:
    calls: dict = {}
    _patch_nas(monkeypatch, calls)

    runner = WorkflowRunner(tmp_path)
    run = runner.run(build_workflow(), inputs={"dry_run": False, "args": []}, dry_run=False)

    assert run.status == "success"
    assert calls.get("json", 0) == 1
    assert calls.get("csv", 0) == 1
    assert calls.get("md", 0) == 1


def test_search_mode_is_readonly(monkeypatch, tmp_path: Path) -> None:
    calls: dict = {}
    _patch_nas(monkeypatch, calls)
    monkeypatch.setattr(steps.legacy, "search_index", lambda q, limit: {"query": q, "match_count": 2, "matches": [{"path": "/a"}, {"path": "/b"}]})

    runner = WorkflowRunner(tmp_path)
    run = runner.run(build_workflow(), inputs={"dry_run": True, "args": ["奥克斯", "--dry-run"]}, dry_run=True)

    assert run.status == "dry_run_success"
    assert calls.get("mount", 0) == 0  # 搜索不挂载
    assert calls.get("json", 0) == 0
    collect = json.loads((runner.last_run_dir / "steps" / "collect_artifacts.json").read_text(encoding="utf-8"))
    assert collect["outputs"]["match_count"] == 2
