from __future__ import annotations

import json
import sys
from pathlib import Path

from core.runtime import WorkflowRunner
from core.runtime.registry import discover_workflow
import tasks.company_nas_listing as task_entry

from workflows.company_nas_listing import steps
from workflows.company_nas_listing.workflow import build_workflow


def _patch(monkeypatch, tmp_path: Path, calls: dict):
    src = tmp_path / "src_model"
    src.mkdir()
    monkeypatch.setattr(steps.legacy, "is_mounted", lambda: False)
    monkeypatch.setattr(steps.legacy, "mount_nas", lambda: calls.__setitem__("mount", calls.get("mount", 0) + 1))
    monkeypatch.setattr(steps.legacy, "unmount_nas", lambda: calls.__setitem__("unmount", calls.get("unmount", 0) + 1))
    monkeypatch.setattr(steps.legacy, "brand_source_dir", lambda b, c: tmp_path)
    monkeypatch.setattr(steps.legacy, "load_nas_index", lambda: {"records": []})
    monkeypatch.setattr(steps.legacy, "target_base_dir", lambda b, c, o: tmp_path / "target")
    monkeypatch.setattr(steps.legacy, "indexed_model_source", lambda b, c, base, pt: (pt, src, "nas_index"))
    monkeypatch.setattr(steps.legacy, "model_target", lambda base, pt: (pt, tmp_path / "target" / pt))
    monkeypatch.setattr(steps.legacy, "selected_files", lambda s, ibs: [src / "a.jpg", src / "b.jpg"])
    monkeypatch.setattr(steps.legacy, "copy_product", lambda s, d, f, replace, dry_run: calls.__setitem__("copy", calls.get("copy", 0) + 1) or (len(f), []))
    monkeypatch.setattr(steps.legacy, "load_jst_rows", lambda p: (["商品编码"], []))
    monkeypatch.setattr(steps.legacy, "match_jst", lambda *a, **k: (None, "remark"))
    monkeypatch.setattr(steps.legacy, "listing_row", lambda *a, **k: ["row"])
    monkeypatch.setattr(steps.legacy, "save_listing", lambda p, rows, title: calls.__setitem__("save", calls.get("save", 0) + 1))
    monkeypatch.setattr(steps.legacy, "validate_outputs", lambda *a, **k: {"ok": True})


def test_workflow_registers() -> None:
    wf = discover_workflow("company_nas_listing")
    assert wf.id == "company_nas_listing"
    assert [s.id for s in wf.steps] == [
        "check_inputs",
        "parse_listing_request",
        "search_nas_index",
        "copy_product_assets",
        "build_listing_data",
        "collect_artifacts",
    ]


def test_dry_run_no_args_is_safe(tmp_path: Path) -> None:
    runner = WorkflowRunner(tmp_path)
    run = runner.run(build_workflow(), inputs={"dry_run": True, "args": ["--dry-run"]}, dry_run=True)
    assert run.status == "dry_run_success"


def test_dry_run_full_args_no_copy_no_excel(monkeypatch, tmp_path: Path) -> None:
    calls: dict = {}
    _patch(monkeypatch, tmp_path, calls)

    runner = WorkflowRunner(tmp_path)
    run = runner.run(
        build_workflow(),
        inputs={"dry_run": True, "args": ["--dry-run", "--brand", "奥克斯", "--category", "足疗机", "--models", "AQA-JT-RFY06"]},
        dry_run=True,
    )

    assert run.status == "dry_run_success"
    assert calls.get("copy", 0) == 0  # 不复制/移动文件
    assert calls.get("save", 0) == 0  # 不生成上架 Excel
    search_step = json.loads((runner.last_run_dir / "steps" / "search_nas_index.json").read_text(encoding="utf-8"))
    assert search_step["outputs"]["items"][0]["selected_files"] == 2


def test_real_run_copies_and_builds_excel(monkeypatch, tmp_path: Path) -> None:
    calls: dict = {}
    _patch(monkeypatch, tmp_path, calls)

    runner = WorkflowRunner(tmp_path)
    run = runner.run(
        build_workflow(),
        inputs={"dry_run": False, "args": ["--brand", "奥克斯", "--category", "足疗机", "--models", "AQA-JT-RFY06"]},
        dry_run=False,
    )

    assert run.status == "success"
    assert calls.get("copy", 0) == 1   # 复制一次
    assert calls.get("save", 0) == 1   # 生成上架 Excel 一次


def test_legacy_main_routes_to_workflow_without_mounting_or_copying(monkeypatch) -> None:
    calls: list[list[str]] = []
    argv = ["company_nas_listing", "--brand", "奥克斯", "--category", "足疗机", "--models", "AQA-JT-RFY06", "--dry-run"]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(task_entry, "_run_workflow", lambda args: calls.append(list(args)) or 0, raising=False)
    monkeypatch.setattr(task_entry, "mount_nas", lambda: (_ for _ in ()).throw(AssertionError("旧入口不应直接挂载 NAS")))
    monkeypatch.setattr(task_entry, "copy_product", lambda *a, **k: (_ for _ in ()).throw(AssertionError("旧入口不应直接复制文件")))

    assert task_entry.main() == 0
    assert calls == [["company_nas_listing", *argv[1:]]]
