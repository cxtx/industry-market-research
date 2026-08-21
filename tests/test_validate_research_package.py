from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from validate_research_package import DATA_FIELDS, EVIDENCE_FIELDS, validate_package  # noqa: E402


def write_csv(path: Path, fields: set[str], rows: list[dict[str, str]]) -> None:
    ordered = sorted(fields)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ordered)
        writer.writeheader()
        writer.writerows(rows)


class ValidateResearchPackageTests(unittest.TestCase):
    def make_valid_package(self, root: Path) -> None:
        (root / "report.md").write_text(
            "# 示例行业报告\n\n市场规模为 100 亿元 [M001]，两年 CAGR 为 10% [M002]。\n",
            encoding="utf-8",
        )
        base_data = {field: "" for field in DATA_FIELDS}
        write_csv(
            root / "data.csv",
            DATA_FIELDS,
            [
                {
                    **base_data,
                    "metric_id": "M001",
                    "metric_name": "市场规模",
                    "value": "100",
                    "unit": "亿元",
                    "geography": "示例地区",
                    "data_period": "2025",
                    "definition": "终端销售额",
                    "evidence_type": "direct",
                    "confidence": "A",
                },
                {
                    **base_data,
                    "metric_id": "M002",
                    "metric_name": "市场 CAGR",
                    "value": "10",
                    "unit": "%",
                    "geography": "示例地区",
                    "data_period": "2023-2025",
                    "definition": "两个复利期间",
                    "evidence_type": "calculated",
                    "confidence": "A",
                    "calculation_operation_id": "growth",
                    "calculation_result_path": "result.percent",
                },
            ],
        )
        base_evidence = {field: "" for field in EVIDENCE_FIELDS}
        write_csv(
            root / "evidence.csv",
            EVIDENCE_FIELDS,
            [
                {
                    **base_evidence,
                    "record_id": "E001",
                    "metric_id": "M001",
                    "source_title": "示例统计表",
                    "publisher": "示例统计机构",
                    "url": "https://example.com/statistics",
                    "accessed_date": "2026-08-21",
                },
                {
                    **base_evidence,
                    "record_id": "E002",
                    "metric_id": "M002",
                    "source_metric_ids": "M001",
                    "calculation_formula": "(121/100)^(1/2)-1",
                },
            ],
        )
        (root / "calculations.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "operations": [
                        {
                            "id": "growth",
                            "type": "cagr",
                            "start_value": 100,
                            "end_value": 121,
                            "periods": 2,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (root / "calculation-results.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "results": [
                        {
                            "id": "growth",
                            "type": "cagr",
                            "input": {"start_value": 100, "end_value": 121, "periods": 2},
                            "result": {"rate": 0.1, "percent": 10.0},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_valid_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.make_valid_package(root)
            result = validate_package(root)
            self.assertTrue(result["valid"], result)
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["warnings"], [])

    def test_unknown_report_marker_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.make_valid_package(root)
            (root / "report.md").write_text("规模为 100 亿元 [M999]。\n", encoding="utf-8")
            result = validate_package(root)
            self.assertFalse(result["valid"])
            self.assertIn("report.md references unknown metric M999", result["errors"])

    def test_estimate_requires_formula_sources_and_assumptions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.make_valid_package(root)
            data_path = root / "data.csv"
            rows, fields = self._read(data_path)
            rows[1]["evidence_type"] = "estimated"
            write_csv(data_path, fields, rows)
            result = validate_package(root)
            self.assertFalse(result["valid"])
            self.assertTrue(any("assumptions required" in error for error in result["errors"]))

    def test_estimate_cannot_claim_high_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.make_valid_package(root)
            data_path = root / "data.csv"
            rows, fields = self._read(data_path)
            rows[1]["evidence_type"] = "estimated"
            rows[1]["confidence"] = "B"
            write_csv(data_path, fields, rows)
            evidence_path = root / "evidence.csv"
            evidence_rows, evidence_fields = self._read(evidence_path)
            evidence_rows[1]["assumptions"] = "示例假设"
            write_csv(evidence_path, evidence_fields, evidence_rows)
            result = validate_package(root)
            self.assertFalse(result["valid"])
            self.assertTrue(any("estimated metrics cannot have B confidence" in error for error in result["errors"]))

    def test_calculation_confidence_cannot_exceed_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.make_valid_package(root)
            data_path = root / "data.csv"
            rows, fields = self._read(data_path)
            rows[0]["confidence"] = "C"
            rows[1]["confidence"] = "B"
            write_csv(data_path, fields, rows)
            result = validate_package(root)
            self.assertFalse(result["valid"])
            self.assertTrue(any("confidence exceeds its weakest input" in error for error in result["errors"]))

    def test_calculation_value_must_match_linked_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.make_valid_package(root)
            data_path = root / "data.csv"
            rows, fields = self._read(data_path)
            rows[1]["value"] = "11"
            write_csv(data_path, fields, rows)
            result = validate_package(root)
            self.assertFalse(result["valid"])
            self.assertTrue(any("does not match calculation result" in error for error in result["errors"]))

    @staticmethod
    def _read(path: Path) -> tuple[list[dict[str, str]], set[str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return [dict(row) for row in reader], set(reader.fieldnames or [])


if __name__ == "__main__":
    unittest.main()
