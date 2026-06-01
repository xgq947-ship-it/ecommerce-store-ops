from __future__ import annotations

import json
import logging
import socket
import subprocess
import time
import urllib.error
import urllib.request
import os
import signal
from pathlib import Path


CDP_HOST = "127.0.0.1"
CDP_PORT = 9222
CDP_URL = f"http://{CDP_HOST}:{CDP_PORT}"
CHROME_BIN = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
PROFILE_DIR = Path.home() / ".sessionhub" / "chrome-9222"


def is_port_open(host: str = CDP_HOST, port: int = CDP_PORT, timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def check_cdp() -> tuple[bool, str]:
    if not is_port_open():
        return False, "9222 端口未开启，Chrome CDP 未启动。"
    try:
        with urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=2) as resp:
            info = json.loads(resp.read().decode("utf-8"))
        browser = info.get("Browser", "Chrome")
        return True, f"Chrome CDP 可用：{browser}"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logging.exception("CDP 连接失败")
        return False, f"9222 端口存在，但 CDP 响应异常：{exc}"


def chrome_start_command() -> str:
    return (
        'open -na "Google Chrome" --args '
        "--remote-debugging-port=9222 "
        '--user-data-dir="$HOME/.sessionhub/chrome-9222" '
        "--new-window about:blank"
    )


def bring_chrome_to_front() -> tuple[bool, str]:
    try:
        subprocess.run(
            [
                "/usr/bin/osascript",
                "-e",
                'tell application "Google Chrome" to activate',
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True, "已将 Chrome 切到前台"
    except Exception as exc:
        return False, f"切换 Chrome 到前台失败：{exc}"


def hide_chrome() -> tuple[bool, str]:
    try:
        subprocess.run(
            [
                "/usr/bin/osascript",
                "-e",
                'tell application "Google Chrome" to hide',
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True, "已将 Chrome 隐藏到后台"
    except Exception as exc:
        return False, f"隐藏 Chrome 失败：{exc}"


def stop_chrome() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["pgrep", "-f", str(PROFILE_DIR)],
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception as exc:
        return False, f"查找专用 Chrome 失败：{exc}"
    pids = []
    for line in result.stdout.splitlines():
        try:
            pid = int(line.strip())
        except ValueError:
            continue
        if pid != os.getpid():
            pids.append(pid)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    for _ in range(20):
        if not is_port_open():
            return True, "已关闭专用 Chrome"
        time.sleep(0.25)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    return True, "已强制关闭专用 Chrome"


def start_chrome(force: bool = False, *, foreground: bool = False) -> tuple[bool, str]:
    ok, msg = check_cdp()
    if ok and not force:
        if foreground:
            bring_chrome_to_front()
        return True, msg
    if force:
        stop_chrome()
    if not CHROME_BIN.exists():
        return False, f"找不到 Chrome：{CHROME_BIN}"
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    launch_cmd = [
        "/usr/bin/open",
        "-g",
        "-na",
        "Google Chrome",
        "--args",
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
        "about:blank",
    ]
    if foreground:
        subprocess.Popen(
            launch_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    else:
        subprocess.Popen(
            launch_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    for _ in range(20):
        ok, msg = check_cdp()
        if ok:
            if foreground:
                bring_chrome_to_front()
            else:
                hide_chrome()
            return True, msg
        time.sleep(0.5)
    logging.error("Chrome CDP 启动超时")
    return False, f"已尝试启动 Chrome，但 CDP 仍不可用。也可以手动运行：\n{chrome_start_command()}"
