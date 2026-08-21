#!/usr/bin/env python3
"""Validate traceability and minimum evidence quality of a research package."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DATA_FIELDS = {
    "metric_id",
    "metric_name",
    "value",
    "unit",
    "geography",
    "data_period",
    "definition",
    "evidence_type",
    "confidence",
    "calculation_operation_id",
    "calculation_result_path",
    "notes",
}
EVIDENCE_FIELDS = {
    "record_id",
    "metric_id",
    "source_title",
    "publisher",
    "url",
    "publication_date",
    "accessed_date",
    "source_location",
    "source_metric_ids",
    "calculation_formula",
    "assumptions",
    "notes",
}
VALID_EVIDENCE_TYPES = {"direct", "calculated", "estimated", "unavailable"}
VALID_CONFIDENCE = {"A", "B", "C", "D"}
CONFIDENCE_RANK = {"A": 4, "B": 3, "C": 2, "D": 1}
METRIC_ID_RE = re.compile(r"^M\d{3,}$")
RECORD_ID_RE = re.compile(r"^E\d{3,}$")
REPORT_MARKER_RE = re.compile(r"\[(M\d{3,})\]")
KEY_NUMBER_RE = re.compile(
    r"(?:[¥￥$€£]\s*\d|\d[\d,.]*\s*(?:%|％|亿元|万元|亿|万|元|美元|人|家|吨|台|件|份|CR\d+|HHI))",
    re.IGNORECASE,
)
INFOGRAPHIC_FILENAME = "core-metrics-infographic.png"
PDF_FILENAME = "report.pdf"
SUMMARY_HEADING_RE = re.compile(
    r"^##\s+(?:\d+(?:\.\d+)*[.、]?\s*)?(?:执行摘要|核心结论|Executive Summary|Key Findings)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
NEXT_H2_RE = re.compile(r"^##\s+", re.MULTILINE)


def _read_csv(path: Path) -> tuple[list[dict[str, str]], set[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        return [dict(row) for row in reader], fields


def _valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _parse_number(value: str) -> float | None:
    normalized = value.strip().replace(",", "")
    try:
        result = float(normalized)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def _resolve_path(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if not part:
            raise KeyError(path)
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            raise KeyError(path)
    return current


def _validated_artifact_name(filename: str, suffix: str, label: str, errors: list[str]) -> str | None:
    candidate = Path(filename)
    if candidate.name != filename or filename in {"", ".", ".."}:
        errors.append(f"{label} must be a filename in the package root, not a path: {filename!r}")
        return None
    if candidate.suffix.lower() != suffix:
        errors.append(f"{label} must use the {suffix} extension: {filename!r}")
        return None
    return filename


def _validate_pdf_visual_artifacts(
    package: Path,
    report: str,
    errors: list[str],
    pdf_file: str,
    infographic_file: str,
) -> None:
    valid_infographic_file = _validated_artifact_name(infographic_file, ".png", "infographic file", errors)
    valid_pdf_file = _validated_artifact_name(pdf_file, ".pdf", "PDF file", errors)
    if valid_infographic_file is None or valid_pdf_file is None:
        return

    infographic = package / valid_infographic_file
    pdf = package / valid_pdf_file

    if not infographic.is_file():
        errors.append(f"missing required file: {valid_infographic_file}")
    else:
        try:
            if infographic.stat().st_size <= 8 or infographic.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
                errors.append(f"{valid_infographic_file} is not a valid non-empty PNG file")
        except OSError as exc:
            errors.append(f"unable to inspect {valid_infographic_file}: {exc}")

    if not pdf.is_file():
        errors.append(f"missing required file: {valid_pdf_file}")
    else:
        try:
            if pdf.stat().st_size <= 5 or pdf.read_bytes()[:5] != b"%PDF-":
                errors.append(f"{valid_pdf_file} is not a valid non-empty PDF file")
        except OSError as exc:
            errors.append(f"unable to inspect {valid_pdf_file}: {exc}")

    infographic_markdown = f"![核心指标信息图]({valid_infographic_file})"
    image_position = report.find(infographic_markdown)
    if image_position < 0:
        errors.append(f"report.md must contain {infographic_markdown!r}")
        return

    summary = SUMMARY_HEADING_RE.search(report)
    if summary is None:
        errors.append("report.md has no recognizable executive-summary or core-conclusions heading")
        return
    next_heading = NEXT_H2_RE.search(report, summary.end())
    summary_end = next_heading.start() if next_heading else len(report)
    if not summary.end() < image_position < summary_end:
        errors.append("core metrics infographic must appear after the summary heading and before the next level-2 heading")


def validate_package(
    package: Path,
    require_pdf_visual: bool = False,
    pdf_file: str = PDF_FILENAME,
    infographic_file: str = INFOGRAPHIC_FILENAME,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    required = {
        "report.md": package / "report.md",
        "data.csv": package / "data.csv",
        "evidence.csv": package / "evidence.csv",
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        return {
            "valid": False,
            "errors": [f"missing required file: {name}" for name in missing],
            "warnings": [],
            "counts": {},
        }

    try:
        report = required["report.md"].read_text(encoding="utf-8-sig")
        data_rows, data_fields = _read_csv(required["data.csv"])
        evidence_rows, evidence_fields = _read_csv(required["evidence.csv"])
    except (OSError, UnicodeError, csv.Error) as exc:
        return {"valid": False, "errors": [f"unable to read package: {exc}"], "warnings": [], "counts": {}}

    missing_data_fields = sorted(DATA_FIELDS - data_fields)
    missing_evidence_fields = sorted(EVIDENCE_FIELDS - evidence_fields)
    if missing_data_fields:
        errors.append(f"data.csv missing fields: {', '.join(missing_data_fields)}")
    if missing_evidence_fields:
        errors.append(f"evidence.csv missing fields: {', '.join(missing_evidence_fields)}")
    if missing_data_fields or missing_evidence_fields:
        return {"valid": False, "errors": errors, "warnings": warnings, "counts": {}}

    calculations_input = package / "calculations.json"
    calculations_output = package / "calculation-results.json"
    calculation_results: dict[str, dict[str, Any]] = {}
    if calculations_input.is_file() and not calculations_output.is_file():
        errors.append("calculations.json exists but calculation-results.json is missing")
    if calculations_output.is_file() and not calculations_input.is_file():
        errors.append("calculation-results.json exists but calculations.json is missing")
    if calculations_output.is_file():
        try:
            calculation_document = json.loads(calculations_output.read_text(encoding="utf-8-sig"))
            raw_results = calculation_document.get("results") if isinstance(calculation_document, dict) else None
            if not isinstance(raw_results, list):
                raise ValueError("root.results must be a list")
            for item in raw_results:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                    raise ValueError("each result must have a string id")
                if item["id"] in calculation_results:
                    raise ValueError(f"duplicate calculation result id: {item['id']}")
                calculation_results[item["id"]] = item
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"invalid calculation-results.json: {exc}")

    metrics: dict[str, dict[str, str]] = {}
    for row_number, row in enumerate(data_rows, start=2):
        metric_id = (row.get("metric_id") or "").strip()
        if not METRIC_ID_RE.fullmatch(metric_id):
            errors.append(f"data.csv row {row_number}: invalid metric_id {metric_id!r}")
            continue
        if metric_id in metrics:
            errors.append(f"data.csv row {row_number}: duplicate metric_id {metric_id}")
            continue
        metrics[metric_id] = row
        evidence_type = (row.get("evidence_type") or "").strip()
        confidence = (row.get("confidence") or "").strip()
        if evidence_type not in VALID_EVIDENCE_TYPES:
            errors.append(f"data.csv row {row_number}: invalid evidence_type {evidence_type!r}")
        if confidence not in VALID_CONFIDENCE:
            errors.append(f"data.csv row {row_number}: invalid confidence {confidence!r}")
        if evidence_type == "estimated" and confidence in {"A", "B"}:
            errors.append(f"data.csv row {row_number}: estimated metrics cannot have {confidence} confidence")
        if evidence_type == "unavailable" and confidence and confidence != "D":
            errors.append(f"data.csv row {row_number}: unavailable metrics must have D confidence")
        if not (row.get("metric_name") or "").strip():
            errors.append(f"data.csv row {row_number}: metric_name is required")
        if not (row.get("definition") or "").strip():
            errors.append(f"data.csv row {row_number}: definition is required")
        if evidence_type != "unavailable":
            for field in ("value", "unit", "geography", "data_period"):
                if not (row.get(field) or "").strip():
                    errors.append(f"data.csv row {row_number}: {field} is required for {evidence_type or 'this metric'}")

        if evidence_type in {"calculated", "estimated"}:
            operation_id = (row.get("calculation_operation_id") or "").strip()
            result_path = (row.get("calculation_result_path") or "").strip()
            metric_value = _parse_number((row.get("value") or ""))
            if metric_value is not None and (not operation_id or not result_path):
                warnings.append(f"{metric_id}: numeric {evidence_type} metric has no calculation result linkage")
            elif operation_id or result_path:
                if not operation_id or not result_path:
                    errors.append(f"data.csv row {row_number}: calculation operation and result path must be provided together")
                elif operation_id not in calculation_results:
                    errors.append(f"data.csv row {row_number}: unknown calculation operation {operation_id!r}")
                else:
                    try:
                        calculated_value = _resolve_path(calculation_results[operation_id], result_path)
                    except KeyError:
                        errors.append(f"data.csv row {row_number}: calculation result path {result_path!r} not found")
                    else:
                        if isinstance(calculated_value, bool) or not isinstance(calculated_value, (int, float)):
                            errors.append(f"data.csv row {row_number}: linked calculation result is not numeric")
                        elif metric_value is not None and not math.isclose(
                            metric_value, float(calculated_value), rel_tol=1e-9, abs_tol=1e-9
                        ):
                            errors.append(
                                f"data.csv row {row_number}: value {metric_value} does not match calculation result {calculated_value}"
                            )

    evidence_by_metric: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    record_ids: set[str] = set()
    for row_number, row in enumerate(evidence_rows, start=2):
        record_id = (row.get("record_id") or "").strip()
        metric_id = (row.get("metric_id") or "").strip()
        if not RECORD_ID_RE.fullmatch(record_id):
            errors.append(f"evidence.csv row {row_number}: invalid record_id {record_id!r}")
        elif record_id in record_ids:
            errors.append(f"evidence.csv row {row_number}: duplicate record_id {record_id}")
        record_ids.add(record_id)
        if metric_id not in metrics:
            errors.append(f"evidence.csv row {row_number}: unknown metric_id {metric_id!r}")
            continue
        evidence_by_metric[metric_id].append((row_number, row))

    for metric_id, metric in metrics.items():
        rows = evidence_by_metric.get(metric_id, [])
        evidence_type = (metric.get("evidence_type") or "").strip()
        if not rows:
            errors.append(f"{metric_id}: no evidence.csv row")
            continue
        for row_number, row in rows:
            if evidence_type == "direct":
                for field in ("source_title", "publisher", "url", "accessed_date"):
                    if not (row.get(field) or "").strip():
                        errors.append(f"evidence.csv row {row_number}: {field} is required for direct evidence")
                url = (row.get("url") or "").strip()
                if url and not _valid_url(url):
                    errors.append(f"evidence.csv row {row_number}: invalid URL {url!r}")
            elif evidence_type in {"calculated", "estimated"}:
                sources = [item.strip() for item in (row.get("source_metric_ids") or "").split(";") if item.strip()]
                if not sources:
                    errors.append(f"evidence.csv row {row_number}: source_metric_ids required for {evidence_type}")
                for source_id in sources:
                    if source_id not in metrics:
                        errors.append(f"evidence.csv row {row_number}: unknown source metric {source_id}")
                    elif source_id == metric_id:
                        errors.append(f"evidence.csv row {row_number}: metric cannot depend on itself")
                target_confidence = (metric.get("confidence") or "").strip()
                source_confidences = [
                    (metrics[source_id].get("confidence") or "").strip()
                    for source_id in sources
                    if source_id in metrics and source_id != metric_id
                ]
                ranked_sources = [CONFIDENCE_RANK[item] for item in source_confidences if item in CONFIDENCE_RANK]
                if (
                    target_confidence in CONFIDENCE_RANK
                    and ranked_sources
                    and CONFIDENCE_RANK[target_confidence] > min(ranked_sources)
                ):
                    errors.append(
                        f"evidence.csv row {row_number}: {metric_id} confidence exceeds its weakest input"
                    )
                if not (row.get("calculation_formula") or "").strip():
                    errors.append(f"evidence.csv row {row_number}: calculation_formula required for {evidence_type}")
                if evidence_type == "estimated" and not (row.get("assumptions") or "").strip():
                    errors.append(f"evidence.csv row {row_number}: assumptions required for estimated evidence")
            elif evidence_type == "unavailable" and not (row.get("notes") or "").strip():
                errors.append(f"evidence.csv row {row_number}: notes required for unavailable metric")

    referenced = set(REPORT_MARKER_RE.findall(report))
    for metric_id in sorted(referenced - set(metrics)):
        errors.append(f"report.md references unknown metric {metric_id}")
    available_metrics = {
        metric_id
        for metric_id, row in metrics.items()
        if (row.get("evidence_type") or "").strip() != "unavailable"
    }
    if available_metrics and not referenced:
        errors.append("report.md contains no metric markers")
    for metric_id in sorted(available_metrics - referenced):
        warnings.append(f"{metric_id}: present in data.csv but not referenced in report.md")

    in_code_fence = False
    for line_number, line in enumerate(report.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence or not stripped or stripped.startswith("#") or REPORT_MARKER_RE.search(line):
            continue
        if set(stripped) <= {"|", "-", ":", " "}:
            continue
        if KEY_NUMBER_RE.search(line):
            warnings.append(f"report.md line {line_number}: possible untagged key number")

    if require_pdf_visual:
        _validate_pdf_visual_artifacts(package, report, errors, pdf_file, infographic_file)

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "metrics": len(metrics),
            "evidence_records": len(evidence_rows),
            "report_metric_references": len(referenced),
            "calculation_results": len(calculation_results),
            "pdf_visual_required": int(require_pdf_visual),
        },
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="directory containing report.md, data.csv and evidence.csv")
    parser.add_argument("--strict", action="store_true", help="treat warnings as a failing result")
    parser.add_argument(
        "--require-pdf-visual",
        action="store_true",
        help="require the selected PDF, PNG and summary placement",
    )
    parser.add_argument(
        "--pdf-file",
        default=PDF_FILENAME,
        help=f"PDF filename in the package root (default: {PDF_FILENAME})",
    )
    parser.add_argument(
        "--infographic-file",
        default=INFOGRAPHIC_FILENAME,
        help=f"infographic PNG filename in the package root (default: {INFOGRAPHIC_FILENAME})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    result = validate_package(
        args.package,
        require_pdf_visual=args.require_pdf_visual,
        pdf_file=args.pdf_file,
        infographic_file=args.infographic_file,
    )
    if args.strict and result["warnings"]:
        result["valid"] = False
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
