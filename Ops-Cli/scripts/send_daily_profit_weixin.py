#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


OPS_ROOT = Path("/Users/dasheng/Desktop/电商Brain/02-运营店铺/Ops-Cli")
OPS_BIN = OPS_ROOT / ".venv/bin/ops"
HERMES_HOME = Path("/Users/dasheng/.hermes")
HERMES_AGENT = HERMES_HOME / "hermes-agent"
HERMES_ENV = HERMES_HOME / ".env"
HERMES_BIN = Path("/Users/dasheng/.local/bin/hermes")


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def run_profit_query() -> dict:
    if not OPS_BIN.exists():
        raise RuntimeError(f"未找到 ops 命令：{OPS_BIN}")
    result = subprocess.run(
        [str(OPS_BIN), "--json", "jst", "profit", "yesterday"],
        cwd=str(OPS_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    output = result.stdout.strip()
    if not output:
        raise RuntimeError(f"利润查询无输出：{result.stderr.strip()}")
    payload = json.loads(output)
    if result.returncode != 0 or not payload.get("success"):
        error = (payload.get("data") or {}).get("error") or result.stderr.strip()
        raise RuntimeError(f"利润查询失败：{error}")
    return payload


def format_message(payload: dict) -> str:
    data = payload["data"]
    profit = float(data["profit"])
    return "\n".join(
        [
            "猫超昨日利润",
            f"日期：{data['date']}",
            f"店铺：{data['store']}",
            f"经营利润：{profit:.2f} 元",
            f"发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]
    )


def send_weixin(message: str) -> dict:
    load_env(HERMES_ENV)
    return _send_weixin_with_retry(message)


def _send_weixin_once(message: str) -> dict:
    sys.path.insert(0, str(HERMES_AGENT))
    from tools.send_message_tool import send_message_tool

    raw = send_message_tool({"target": "weixin", "message": message})
    result = json.loads(raw)
    if not result.get("success"):
        raise RuntimeError(result.get("error") or raw)
    return result


def _clear_home_context_token() -> bool:
    account_id = os.getenv("WEIXIN_ACCOUNT_ID", "").strip()
    home_channel = os.getenv("WEIXIN_HOME_CHANNEL", "").strip()
    if not account_id or not home_channel:
        return False
    path = HERMES_HOME / "weixin" / "accounts" / f"{account_id}.context-tokens.json"
    if not path.exists():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    if home_channel not in data:
        return False
    data.pop(home_channel, None)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def _restart_gateway() -> None:
    if not HERMES_BIN.exists():
        return
    subprocess.run(
        [str(HERMES_BIN), "gateway", "restart"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
    )


def _send_weixin_with_retry(message: str) -> dict:
    try:
        return _send_weixin_once(message)
    except RuntimeError as exc:
        error = str(exc)
        should_refresh = "ret=-2" in error or "errcode=-14" in error or "context_token" in error
        if not should_refresh:
            raise
        _clear_home_context_token()
        _restart_gateway()
        time.sleep(8)
        return _send_weixin_once(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send JST daily profit to Weixin through Hermes.")
    parser.add_argument("--no-send", action="store_true", help="Only query and print the message.")
    args = parser.parse_args()

    try:
        payload = run_profit_query()
        message = format_message(payload)
        send_result = None if args.no_send else send_weixin(message)
        print(json.dumps({"success": True, "message": message, "send_result": send_result}, ensure_ascii=False))
        return 0
    except Exception as exc:
        failure_message = "\n".join(
            [
                "猫超昨日利润自动查询失败",
                f"错误：{exc}",
                f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ]
        )
        if not args.no_send:
            try:
                send_weixin(failure_message)
            except Exception as send_exc:
                print(
                    json.dumps(
                        {"success": False, "error": str(exc), "send_error": str(send_exc)},
                        ensure_ascii=False,
                    )
                )
                return 1
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
