from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "send_monthly_profit_feishu.py"
SPEC = importlib.util.spec_from_file_location("send_monthly_profit_feishu", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_previous_month_handles_year_boundary() -> None:
    assert MODULE.previous_month(date(2026, 1, 1)) == "2025-12"


def test_format_message_monthly_profit() -> None:
    payload = {
        "data": {
            "month": "2026-04",
            "store": "（猫超）福安市启明工贸有限公司（肖国清）",
            "profit": 19087.81,
            "metric_field": "经营利润",
        }
    }

    assert MODULE.format_message(payload) == (
        "📊 猫超月利润简报\n"
        "📅 2026年4月\n"
        "🏪 （猫超）福安市启明工贸有限公司\n"
        "━━━━━━━━━━━━━━━━━\n"
        "💰 经营利润  ¥19,087.81"
    )
