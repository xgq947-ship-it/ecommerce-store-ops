from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.tmall_product_list import main as tmall_product_main


def test_parse_args_no_longer_accepts_work_dir(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["tmall_product_list", "--work-dir", "/tmp/legacy-workdir"],
    )

    with pytest.raises(SystemExit) as exc_info:
        tmall_product_main.parse_args()

    assert exc_info.value.code == 2
