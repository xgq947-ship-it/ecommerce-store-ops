from __future__ import annotations

import json
import subprocess

from clients import ops_cli_client


def _completed(returncode: int, payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["ops"],
        returncode=returncode,
        stdout=json.dumps(payload, ensure_ascii=False),
        stderr="",
    )


def test_run_ops_json_retries_auth_required_by_default_for_real_command(monkeypatch) -> None:
    calls: list[list[str]] = []
    results = [
        _completed(
            1,
            {
                "success": False,
                "data": {
                    "error_code": "AUTH_REQUIRED",
                    "error": "session 不可用",
                    "context_path": "runtime/context/first.json",
                },
            },
        ),
        _completed(0, {"success": True, "data": {"ok": True}}),
    ]

    monkeypatch.setattr(ops_cli_client, "_command_prefix", lambda: ["ops"])
    monkeypatch.setattr(ops_cli_client.sys.stdin, "isatty", lambda: True)

    def fake_run(command, **kwargs):
        calls.append(command)
        return results.pop(0)

    monkeypatch.setattr(ops_cli_client.subprocess, "run", fake_run)

    payload = ops_cli_client.run_ops_json(["--json", "jst", "order", "reimburse"])

    assert payload["success"] is True
    assert calls == [
        ["ops", "--json", "jst", "order", "reimburse"],
        ["ops", "--interactive-login", "--json", "jst", "order", "reimburse"],
    ]


def test_run_ops_json_does_not_retry_without_tty(monkeypatch) -> None:
    calls: list[list[str]] = []
    result = _completed(
        1,
        {
            "success": False,
            "data": {
                "error_code": "AUTH_REQUIRED",
                "error": "session 不可用",
                "context_path": "runtime/context/first.json",
            },
        },
    )

    monkeypatch.setattr(ops_cli_client, "_command_prefix", lambda: ["ops"])
    monkeypatch.setattr(ops_cli_client.sys.stdin, "isatty", lambda: False)

    def fake_run(command, **kwargs):
        calls.append(command)
        return result

    monkeypatch.setattr(ops_cli_client.subprocess, "run", fake_run)

    try:
        ops_cli_client.run_ops_json(["--json", "jst", "order", "reimburse"], interactive_recovery=True)
    except RuntimeError as exc:
        assert "AUTH_REQUIRED" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")

    assert calls == [["ops", "--json", "jst", "order", "reimburse"]]


def test_run_ops_json_does_not_retry_dry_run_by_default(monkeypatch) -> None:
    calls: list[list[str]] = []
    result = _completed(
        1,
        {
            "success": False,
            "data": {
                "error_code": "AUTH_REQUIRED",
                "error": "session 不可用",
                "context_path": "runtime/context/first.json",
            },
        },
    )

    monkeypatch.setattr(ops_cli_client, "_command_prefix", lambda: ["ops"])
    monkeypatch.setattr(ops_cli_client.sys.stdin, "isatty", lambda: True)

    def fake_run(command, **kwargs):
        calls.append(command)
        return result

    monkeypatch.setattr(ops_cli_client.subprocess, "run", fake_run)

    try:
        ops_cli_client.run_ops_json(["--json", "jst", "product", "sync", "--dry-run"])
    except RuntimeError as exc:
        assert "AUTH_REQUIRED" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")

    assert calls == [["ops", "--json", "jst", "product", "sync", "--dry-run"]]
