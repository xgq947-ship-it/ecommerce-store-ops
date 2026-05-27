#!/usr/bin/env python3
"""Unified entry point for local operations automation."""

from __future__ import annotations

import argparse
import json
import importlib.util
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from core.config_loader import get_path
from core.task_context import TaskContext
from core.task_registry import resolve_task, task_scripts


ROOT = Path(__file__).resolve().parent
LOG_DIR = get_path("logs_dir")
BUNDLED_PYTHON = Path("/Users/dasheng/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3")

TASK_REQUIRED_MODULES = {
    "append_brush_orders": ("openpyxl",),
    "tag_jst_brush_orders": (),
    "jst_brush_reimburse_workorder": ("requests", "openpyxl"),
    "company_nas_listing": ("openpyxl",),
    "company_nas_index": ("openpyxl",),
    "buyer_show": ("openpyxl", "PIL"),
    "update_jst_products": (),
    "update_maochao_goods": ("openpyxl",),
    "tmcs_sync_jst_shop_goods": ("openpyxl",),
    "process_maochao_bills": ("openpyxl",),
}

TASKS = task_scripts()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运营自动化工具统一入口")
    parser.add_argument("--list", action="store_true", help="列出当前已注册任务，不执行业务")
    parser.add_argument("task", nargs="?", help="要执行的任务，支持相近说法")
    parser.add_argument("task_args", nargs=argparse.REMAINDER, help="传给任务脚本的参数")
    args = parser.parse_args()
    if args.list:
        return args
    if not args.task:
        parser.error("缺少任务名；可用 --list 查看已注册任务")
    first_flag_index = next((index for index, part in enumerate(args.task_args) if part.startswith("-")), len(args.task_args))
    natural_parts = args.task_args[:first_flag_index]
    option_parts = args.task_args[first_flag_index:]
    raw_text = " ".join([args.task, *natural_parts]).strip()
    resolved_task = resolve_task(args.task)
    if resolved_task != "company_nas_listing" and raw_text != args.task:
        try:
            resolved_task = resolve_task(raw_text)
        except SystemExit:
            pass
    args.task = resolved_task
    if args.task == "company_nas_listing" and raw_text != "company_nas_listing" and "--text" not in option_parts:
        args.task_args = ["--text", raw_text, *option_parts]
    return args


def python_has_modules(python_path: Path, modules: tuple[str, ...]) -> bool:
    if not python_path.exists():
        return False
    command = [
        str(python_path),
        "-c",
        "import importlib.util, sys; "
        "mods=sys.argv[1:]; "
        "missing=[m for m in mods if importlib.util.find_spec(m) is None]; "
        "raise SystemExit(1 if missing else 0)",
        *modules,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode == 0


def python_candidates() -> list[Path]:
    candidates = [
        BUNDLED_PYTHON,
        Path(sys.executable),
        Path("/usr/bin/python3"),
        Path("/usr/local/bin/python3"),
        Path("/opt/homebrew/bin/python3"),
    ]
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def choose_python(task_name: str) -> str:
    required_modules = TASK_REQUIRED_MODULES.get(task_name, ())
    for candidate in python_candidates():
        if python_has_modules(candidate, required_modules):
            return str(candidate)
    return sys.executable


def write_log(task: str, payload: dict) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = LOG_DIR / f"{task}_{stamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    args = parse_args()
    if args.list:
        for task_name, task_script in sorted(TASKS.items()):
            print(f"{task_name}\t{task_script}")
        return 0
    context = TaskContext(args.task)
    context.add_input("task_args", args.task_args)
    task_script = TASKS[args.task]
    if not task_script.exists():
        message = f"任务脚本不存在：{task_script}"
        context.add_error(message)
        context_path = context.finish("failed")
        print(message, file=sys.stderr)
        print(f"任务上下文：{context_path}")
        return 2

    command = [choose_python(args.task), str(task_script), *args.task_args]
    context.add_input("command", command)
    started_at = datetime.now().isoformat(timespec="seconds")
    result = subprocess.run(command, text=True, capture_output=True)
    finished_at = datetime.now().isoformat(timespec="seconds")

    parsed_stdout = None
    try:
        parsed_stdout = json.loads(result.stdout) if result.stdout.strip().startswith("{") else None
    except json.JSONDecodeError:
        parsed_stdout = None

    log_payload = {
        "task": args.task,
        "started_at": started_at,
        "finished_at": finished_at,
        "returncode": result.returncode,
        "command": command,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "parsed_stdout": parsed_stdout,
    }
    log_path = write_log(args.task, log_payload)
    dry_run = "--dry-run" in args.task_args
    context.add_output("returncode", result.returncode)
    context.add_output("started_at", started_at)
    context.add_output("finished_at", finished_at)
    context.add_output("log_path", log_path)
    context.add_artifact(log_path, kind="run_log")
    if parsed_stdout is not None:
        context.add_output("parsed_stdout", parsed_stdout)
        for key in ("latest_file", "import_file", "source", "root", "work_dir"):
            if isinstance(parsed_stdout, dict) and parsed_stdout.get(key):
                context.add_artifact(str(parsed_stdout[key]), kind=key)
        if isinstance(parsed_stdout, dict):
            reports = parsed_stdout.get("reports")
            if isinstance(reports, dict):
                for key, value in reports.items():
                    if value:
                        context.add_artifact(str(value), kind=key)
            if parsed_stdout.get("task_log_path"):
                context.add_artifact(str(parsed_stdout["task_log_path"]), kind="task_log")
    if result.returncode != 0:
        context.add_error(
            f"任务退出码：{result.returncode}",
            {
                "stderr_tail": result.stderr[-1000:],
                "stdout_tail": result.stdout[-1000:],
                "traceback": _brief_traceback(result.stderr),
            },
        )
        context_status = "failed"
    elif dry_run:
        context_status = "dry_run_success"
    else:
        context_status = "success"
    context_path = context.finish(context_status)

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    print(f"\n日志：{log_path}")
    print(f"任务上下文：{context_path}")

    return result.returncode


def _brief_traceback(stderr: str) -> str:
    if "Traceback" not in stderr:
        return ""
    lines = [line for line in stderr.strip().splitlines() if line.strip()]
    return "\n".join(lines[-8:])


if __name__ == "__main__":
    raise SystemExit(main())
