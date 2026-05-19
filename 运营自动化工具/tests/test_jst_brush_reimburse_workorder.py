from __future__ import annotations

import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from tasks import jst_brush_reimburse_workorder as reimburse


class OpsReimburseTests(unittest.TestCase):
    def test_query_reimburse_candidate_uses_ops_cli(self) -> None:
        order = reimburse.BatchOrder(
            row_index=3,
            brusher="唐杨",
            brush_date="5月19日",
            order_no="OUTER001",
            order_amount=Decimal("95"),
            commission_amount=Decimal("14"),
            product_code="SKU001",
            product_name="商品名",
        )
        batch = reimburse.BatchInfo(
            workbook_path=Path("/tmp/登记表.xlsx"),
            start_row=3,
            end_row=3,
            orders=[order],
            principal_total=Decimal("95"),
            payout_total=Decimal("14"),
        )
        payload = {
            "success": True,
            "data": {
                "outer_order_id": "OUTER001",
                "internal_order_id": "123",
                "online_order_id": "LP001",
                "item_name": "聚水潭商品名",
                "has_existing_workorder": False,
                "existing_detail": {},
            },
        }

        with patch.object(reimburse, "run_ops_json", return_value=payload) as run_ops:
            candidate, checked = reimburse.choose_candidate(batch)

        self.assertEqual(candidate.o_id, "123")
        self.assertEqual(candidate.lp_order_no, "LP001")
        self.assertEqual(candidate.item_name, "聚水潭商品名")
        self.assertEqual(len(checked), 1)
        command = run_ops.call_args.args[0]
        self.assertIn("reimburse", command)
        self.assertIn("--outer-order-id", command)
        self.assertIn("OUTER001", command)


if __name__ == "__main__":
    unittest.main()
