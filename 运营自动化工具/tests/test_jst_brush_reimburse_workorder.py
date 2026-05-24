from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
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
        self.assertEqual(run_ops.call_args.kwargs, {"interactive_recovery": False})
        self.assertIn("reimburse", command)
        self.assertIn("--outer-order-id", command)
        self.assertIn("OUTER001", command)

    def test_real_candidate_check_enables_interactive_recovery(self) -> None:
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
            reimburse.choose_candidate(batch, interactive_recovery=True)

        self.assertEqual(run_ops.call_args.kwargs, {"interactive_recovery": True})

    def test_failed_candidate_checks_are_not_reported_as_existing_workorders(self) -> None:
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
        checked = [
            reimburse.CandidateResult(
                order=order,
                skip_reason="Ops-Cli 执行失败 [AUTH_REQUIRED]：session 不可用",
            )
        ]
        output = io.StringIO()

        with (
            patch.object(reimburse, "parse_args", return_value=SimpleNamespace(input="/tmp/登记表.xlsx", order_no=None, dry_run=False)),
            patch.object(reimburse, "setup_logging", return_value=Path("/tmp/reimburse.log")),
            patch.object(reimburse, "read_current_batch", return_value=batch),
            patch.object(reimburse, "choose_candidate", return_value=(None, checked)),
            patch.object(reimburse, "write_failed_export", return_value=Path("/tmp/failed.xlsx")),
            redirect_stdout(output),
        ):
            result = reimburse.main()

        self.assertEqual(result, 1)
        self.assertIn("状态核验失败", output.getvalue())
        self.assertNotIn("所有订单均已存在报销工单", output.getvalue())


if __name__ == "__main__":
    unittest.main()
