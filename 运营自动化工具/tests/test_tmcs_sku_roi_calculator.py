from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflows.tmcs_sku_roi.roi_calculator import calculate_roi


def test_calculate_roi_returns_three_values() -> None:
    result = calculate_roi(799, 361)

    assert result["break_even_roi"] is not None
    assert result["safe_roi"] is not None
    assert result["ideal_roi"] == pytest.approx(8.3333333333)


def test_calculate_roi_uses_promotion_ratio_for_ideal_roi() -> None:
    result = calculate_roi(1000, 100, config={"ideal_promotion_ratio": 0.04})

    assert result["ideal_roi"] == pytest.approx(25.0)


def test_calculate_roi_rejects_invalid_price() -> None:
    with pytest.raises(ValueError, match="淘系控价"):
        calculate_roi("", 100)
