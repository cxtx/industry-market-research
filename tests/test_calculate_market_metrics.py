from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from calculate_market_metrics import CalculationError, calculate_document  # noqa: E402


class CalculateMarketMetricsTests(unittest.TestCase):
    def test_all_operation_types(self) -> None:
        document = {
            "schema_version": "1.0",
            "operations": [
                {
                    "id": "growth",
                    "type": "cagr",
                    "start_value": 100,
                    "end_value": 121,
                    "periods": 2,
                },
                {
                    "id": "shares",
                    "type": "market_share",
                    "market_total": 100,
                    "entities": [
                        {"name": "A", "value": 40},
                        {"name": "B", "value": 30},
                    ],
                },
                {
                    "id": "margin",
                    "type": "margin",
                    "numerator": -10,
                    "denominator": 100,
                },
                {
                    "id": "wages",
                    "type": "summary",
                    "values": [10, 20, 30],
                    "weights": [1, 2, 1],
                },
                {
                    "id": "top_down",
                    "type": "product",
                    "factors": [
                        {"name": "parent_market", "value": 200},
                        {"name": "segment_share", "value": 0.25},
                    ],
                },
                {
                    "id": "forecast",
                    "type": "scenario_forecast",
                    "base_value": 100,
                    "years": 2,
                    "annual_rates": {"low": 0.0, "base": 0.1},
                },
            ],
        }

        results = {item["id"]: item["result"] for item in calculate_document(document)["results"]}
        self.assertAlmostEqual(results["growth"]["percent"], 10.0)
        self.assertEqual(results["shares"]["covered_percent"], 70.0)
        self.assertEqual(results["shares"]["unallocated_percent"], 30.0)
        self.assertEqual(results["shares"]["cr3_known_lower_bound_percent"], 70.0)
        self.assertNotIn("cr3_percent", results["shares"])
        self.assertEqual(results["shares"]["hhi_known_brands_lower_bound"], 2500.0)
        self.assertFalse(results["shares"]["hhi_complete"])
        self.assertEqual(results["margin"]["percent"], -10.0)
        self.assertEqual(results["wages"]["median"], 20.0)
        self.assertEqual(results["wages"]["weighted_mean"], 20.0)
        self.assertEqual(results["top_down"]["product"], 50.0)
        self.assertAlmostEqual(results["forecast"]["scenarios"]["base"]["final_value"], 121.0)

    def test_complete_share_has_exact_hhi(self) -> None:
        document = {
            "schema_version": "1.0",
            "operations": [
                {
                    "id": "shares",
                    "type": "market_share",
                    "market_total": 100,
                    "entities": [
                        {"name": "A", "value": 60},
                        {"name": "B", "value": 40},
                    ],
                }
            ],
        }
        result = calculate_document(document)["results"][0]["result"]
        self.assertTrue(result["hhi_complete"])
        self.assertEqual(result["hhi"], 5200.0)
        self.assertEqual(result["cr3_percent"], 100.0)
        self.assertNotIn("hhi_known_brands_lower_bound", result)

    def test_top_n_complete_allows_exact_cr(self) -> None:
        document = {
            "schema_version": "1.0",
            "operations": [
                {
                    "id": "shares",
                    "type": "market_share",
                    "market_total": 100,
                    "top_n_complete": 3,
                    "entities": [
                        {"name": "A", "value": 40},
                        {"name": "B", "value": 25},
                        {"name": "C", "value": 15},
                    ],
                }
            ],
        }
        result = calculate_document(document)["results"][0]["result"]
        self.assertEqual(result["cr3_percent"], 80.0)
        self.assertEqual(result["cr5_known_lower_bound_percent"], 80.0)

    def test_rejects_inconsistent_share_denominator(self) -> None:
        document = {
            "schema_version": "1.0",
            "operations": [
                {
                    "id": "bad",
                    "type": "market_share",
                    "market_total": 100,
                    "entities": [{"name": "A", "value": 101}],
                }
            ],
        }
        with self.assertRaisesRegex(CalculationError, "exceed market_total"):
            calculate_document(document)

    def test_rejects_duplicate_operation_id(self) -> None:
        document = {
            "schema_version": "1.0",
            "operations": [
                {"id": "same", "type": "margin", "numerator": 1, "denominator": 2},
                {"id": "same", "type": "margin", "numerator": 1, "denominator": 2},
            ],
        }
        with self.assertRaisesRegex(CalculationError, "duplicate operation id"):
            calculate_document(document)

    def test_product_rejects_duplicate_factor_name(self) -> None:
        document = {
            "schema_version": "1.0",
            "operations": [
                {
                    "id": "bad_product",
                    "type": "product",
                    "factors": [
                        {"name": "same", "value": 2},
                        {"name": "same", "value": 3},
                    ],
                }
            ],
        }
        with self.assertRaisesRegex(CalculationError, "duplicate factor name"):
            calculate_document(document)


if __name__ == "__main__":
    unittest.main()
