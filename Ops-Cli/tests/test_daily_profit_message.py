from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "send_daily_profit_weixin.py"
SPEC = importlib.util.spec_from_file_location("send_daily_profit_weixin", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_format_message_is_a_single_short_profit_line() -> None:
    payload = {
        "data": {
            "date": "2026-05-27",
            "store": "（猫超）福安市启明工贸有限公司（肖国清）",
            "profit": 3596.03,
        }
    }

    assert MODULE.format_message(payload) == "5月27日猫超利润：3596.03元"
