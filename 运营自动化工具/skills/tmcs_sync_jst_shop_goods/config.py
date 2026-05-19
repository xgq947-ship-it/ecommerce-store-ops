from __future__ import annotations

from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SKILL_DIR.parents[1]
OPS_CLI_ROOT = Path("/Users/dasheng/Desktop/电商Brain/02-运营店铺/Ops-Cli")
OPS_BIN = OPS_CLI_ROOT / ".venv" / "bin" / "ops"

DATA_DIR = SKILL_DIR / "data"
OUTPUT_DIR = SKILL_DIR / "output"
LOG_DIR = SKILL_DIR / "logs"
SCREENSHOT_DIR = SKILL_DIR / "screenshots"

DEFAULT_WAREHOUSE_CODE = "mc_aokesi_suolong"
DEFAULT_JST_SHOP_NAME = "（猫超）启明工贸有限公司"


def ensure_dirs() -> None:
    for path in (DATA_DIR, OUTPUT_DIR, LOG_DIR, SCREENSHOT_DIR):
        path.mkdir(parents=True, exist_ok=True)
