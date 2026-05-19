#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.retry_queue import list_retries, mark_done, replay_all, replay_retry  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="查看或重放失败任务队列")
    parser.add_argument("retry_id", nargs="?", help="指定 retry_id；不填则查看队列")
    parser.add_argument("--all", action="store_true", help="重放全部 pending retry")
    parser.add_argument("--done", action="store_true", help="把指定 retry_id 标记为 done")
    parser.add_argument("--execute", action="store_true", help="允许真实执行；默认只 dry-run")
    return parser.parse_args()


def print_retries(rows: list[dict]) -> None:
    if not rows:
        print("重试队列为空。")
        return
    print(f"待重试任务：{len(rows)} 个")
    for row in rows:
        print(f"- {row.get('retry_id')} | {row.get('task_name')} | {row.get('reason')} | {row.get('payload')}")


def main() -> int:
    args = parse_args()
    if args.done:
        if not args.retry_id:
            raise SystemExit("--done 需要指定 retry_id")
        path = mark_done(args.retry_id)
        print(f"已标记完成：{path}")
        return 0

    if args.all:
        results = replay_all(execute=args.execute)
        print(json.dumps({"execute": args.execute, "results": results}, ensure_ascii=False, indent=2))
        return 0 if all(item["returncode"] == 0 for item in results) else 1

    if args.retry_id:
        result = replay_retry(args.retry_id, execute=args.execute)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(result["returncode"])

    print_retries(list_retries())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
