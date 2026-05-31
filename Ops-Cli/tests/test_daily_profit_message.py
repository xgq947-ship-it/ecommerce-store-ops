from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "send_daily_profit_weixin.py"
SPEC = importlib.util.spec_from_file_location("send_daily_profit_weixin", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_format_message_card_style_with_emoji() -> None:
    payload = {
        "data": {
            "date": "2026-05-27",
            "store": "（猫超）福安市启明工贸有限公司（肖国清）",
            "profit": 3596.03,
        }
    }

    assert MODULE.format_message(payload) == (
        "💰 猫超经营利润日报\n"
        "\n"
        "📅 5月27日 周三\n"
        "💎 经营利润\n"
        "\n"
        "     ¥3,596.03\n"
        "\n"
        "🏪 （猫超）福安市启明工贸有限公司"
    )
