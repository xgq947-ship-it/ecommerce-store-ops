from __future__ import annotations

import json
from pathlib import Path

from core.runtime import WorkflowRunner
from core.runtime.registry import discover_workflow

from workflows.retry_queue import steps
from workflows.retry_queue.workflow import build_workflow


def _patch(monkeypatch, calls: dict, rows=None):
    monkeypatch.setattr(steps.legacy, "list_retries", lambda: rows if rows is not None else [{"retry_id": "r1", "task_name": "t", "reason": "x"}])
    monkeypatch.setattr(steps.legacy, "replay_all", lambda execute=False: calls.__setitem__("replay_all", {"execute": execute}) or [])
    monkeypatch.setattr(steps.legacy, "replay_retry", lambda rid, execute=False: calls.__setitem__("replay_one", {"id": rid, "execute": execute}) or {"returncode": 0})
    monkeypatch.setattr(steps.legacy, "mark_done", lambda rid: calls.__setitem__("done", rid) or Path("/tmp/r1.json"))


def test_workflow_registers() -> None:
    wf = discover_workflow("retry_queue")
    assert wf.id == "retry_queue"
    assert [s.id for s in wf.steps] == [
        "check_inputs",
        "load_retry_items",
        "preview_retry",
        "execute_retry",
        "collect_outputs",
    ]


def test_dry_run_view_only(monkeypatch, tmp_path: Path) -> None:
    calls: dict = {}
    _patch(monkeypatch, calls)

    runner = WorkflowRunner(tmp_path)
    run = runner.run(build_workflow(), inputs={"dry_run": True, "args": ["--dry-run"]}, dry_run=True)

    assert run.status == "dry_run_success"
    assert "replay_all" not in calls and "replay_one" not in calls and "done" not in calls
    exec_step = json.loads((runner.last_run_dir / "steps" / "execute_retry.json").read_text(encoding="utf-8"))
    assert exec_step["outputs"]["skipped"] is True


def test_dry_run_all_forces_no_execute(monkeypatch, tmp_path: Path) -> None:
    calls: dict = {}
    _patch(monkeypatch, calls)

    runner = WorkflowRunner(tmp_path)
    runner.run(build_workflow(), inputs={"dry_run": True, "args": ["--all", "--dry-run", "--execute"]}, dry_run=True)

    # 即使带 --execute，dry-run 也强制 execute=False
    assert calls["replay_all"]["execute"] is False


def test_real_all_with_execute(monkeypatch, tmp_path: Path) -> None:
    calls: dict = {}
    _patch(monkeypatch, calls)

    runner = WorkflowRunner(tmp_path)
    run = runner.run(build_workflow(), inputs={"dry_run": False, "args": ["--all", "--execute"]}, dry_run=False)

    assert run.status == "success"
    assert calls["replay_all"]["execute"] is True


def test_done_skipped_in_dry_run(monkeypatch, tmp_path: Path) -> None:
    calls: dict = {}
    _patch(monkeypatch, calls)

    runner = WorkflowRunner(tmp_path)
    runner.run(build_workflow(), inputs={"dry_run": True, "args": ["r1", "--done", "--dry-run"]}, dry_run=True)

    assert "done" not in calls  # dry-run 不 mark_done


def test_done_real_marks(monkeypatch, tmp_path: Path) -> None:
    calls: dict = {}
    _patch(monkeypatch, calls)

    runner = WorkflowRunner(tmp_path)
    runner.run(build_workflow(), inputs={"dry_run": False, "args": ["r1", "--done"]}, dry_run=False)

    assert calls.get("done") == "r1"
