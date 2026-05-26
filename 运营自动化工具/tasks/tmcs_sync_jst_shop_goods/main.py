#!/usr/bin/env python3
"""Expose the existing TMCS-to-JST skill through the unified task runner."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_ENTRY = ROOT / "skills" / "tmcs_sync_jst_shop_goods" / "main.py"


def main() -> int:
    sys.argv.insert(1, "run")
    runpy.run_path(str(SKILL_ENTRY), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
