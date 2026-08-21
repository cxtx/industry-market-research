#!/usr/bin/env python3
"""Deterministic calculations for industry market research packages."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any


class CalculationError(ValueError):
    """Raised when an operation is invalid or would produce misleading output."""


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalculationError(f"{field} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise CalculationError(f"{field} must be finite")
    return result


def _positive(value: Any, field: str) -> float:
    result = _number(value, field)
    if result <= 0:
        raise CalculationError(f"{field} must be greater than zero")
    return result


def _nonnegative(value: Any, field: str) -> float:
    result = _number(value, field)
    if result < 0:
        raise CalculationError(f"{field} must be non-negative")
    return result


def _clean(value: float) -> float:
    return round(value, 12)


def calculate_cagr(operation: dict[str, Any]) -> dict[str, Any]:
    start = _positive(operation.get("start_value"), "start_value")
    end = _nonnegative(operation.get("end_value"), "end_value")
    periods = _positive(operation.get("periods"), "periods")
    rate = (end / start) ** (1.0 / periods) - 1.0
    return {"rate": _clean(rate), "percent": _clean(rate * 100.0)}


def calculate_market_share(operation: dict[str, Any]) -> dict[str, Any]:
    total = _positive(operation.get("market_total"), "market_total")
    entities = operation.get("entities")
    if not isinstance(entities, list) or not entities:
        raise CalculationError("entities must be a non-empty list")

    values: list[tuple[str, float]] = []
    names: set[str] = set()
    for index, entity in enumerate(entities):
        if not isinstance(entity, dict):
            raise CalculationError(f"entities[{index}] must be an object")
        name = entity.get("name")
        if not isinstance(name, str) or not name.strip():
            raise CalculationError(f"entities[{index}].name must be a non-empty string")
        name = name.strip()
        if name in names:
            raise CalculationError(f"duplicate entity name: {name}")
        names.add(name)
        value = _nonnegative(entity.get("value"), f"entities[{index}].value")
        values.append((name, value))

    observed = sum(value for _, value in values)
    tolerance = max(1e-9, total * 1e-9)
    if observed > total + tolerance:
        raise CalculationError(
            f"entity values ({observed}) exceed market_total ({total}); check denominator and units"
        )

    shares = [(name, value / total * 100.0) for name, value in values]
    ranked = sorted(shares, key=lambda item: item[1], reverse=True)
    covered = observed / total * 100.0
    raw_top_n_complete = operation.get("top_n_complete", 0)
    if (
        isinstance(raw_top_n_complete, bool)
        or not isinstance(raw_top_n_complete, int)
        or raw_top_n_complete < 0
        or raw_top_n_complete > len(values)
    ):
        raise CalculationError("top_n_complete must be an integer between 0 and the number of entities")
    result: dict[str, Any] = {
        "shares_percent": {name: _clean(share) for name, share in shares},
        "covered_percent": _clean(covered),
        "unallocated_percent": _clean(max(0.0, 100.0 - covered)),
        "top_n_complete": raw_top_n_complete,
    }
    complete = math.isclose(covered, 100.0, rel_tol=0.0, abs_tol=1e-7)
    for count in (3, 5, 10):
        concentration = _clean(sum(share for _, share in ranked[:count]))
        if complete or raw_top_n_complete >= count:
            result[f"cr{count}_percent"] = concentration
        else:
            result[f"cr{count}_known_lower_bound_percent"] = concentration

    hhi_known = sum(share**2 for _, share in ranked)
    result["hhi_complete"] = complete
    if complete:
        result["hhi"] = _clean(hhi_known)
    else:
        result["hhi_known_brands_lower_bound"] = _clean(hhi_known)
    return result


def calculate_margin(operation: dict[str, Any]) -> dict[str, Any]:
    numerator = _number(operation.get("numerator"), "numerator")
    denominator = _positive(operation.get("denominator"), "denominator")
    rate = numerator / denominator
    return {"rate": _clean(rate), "percent": _clean(rate * 100.0)}


def calculate_product(operation: dict[str, Any]) -> dict[str, Any]:
    factors = operation.get("factors")
    if not isinstance(factors, list) or not factors:
        raise CalculationError("factors must be a non-empty list")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    product = 1.0
    for index, factor in enumerate(factors):
        if not isinstance(factor, dict):
            raise CalculationError(f"factors[{index}] must be an object")
        name = factor.get("name")
        if not isinstance(name, str) or not name.strip():
            raise CalculationError(f"factors[{index}].name must be a non-empty string")
        name = name.strip()
        if name in seen:
            raise CalculationError(f"duplicate factor name: {name}")
        seen.add(name)
        value = _nonnegative(factor.get("value"), f"factors[{index}].value")
        product *= value
        normalized.append({"name": name, "value": _clean(value)})
    return {"factors": normalized, "product": _clean(product)}


def calculate_summary(operation: dict[str, Any]) -> dict[str, Any]:
    raw_values = operation.get("values")
    if not isinstance(raw_values, list) or not raw_values:
        raise CalculationError("values must be a non-empty list")
    values = [_number(value, f"values[{index}]") for index, value in enumerate(raw_values)]
    result: dict[str, Any] = {
        "count": len(values),
        "mean": _clean(statistics.fmean(values)),
        "median": _clean(statistics.median(values)),
        "minimum": _clean(min(values)),
        "maximum": _clean(max(values)),
    }

    raw_weights = operation.get("weights")
    if raw_weights is not None:
        if not isinstance(raw_weights, list) or len(raw_weights) != len(values):
            raise CalculationError("weights must be a list with the same length as values")
        weights = [
            _nonnegative(weight, f"weights[{index}]")
            for index, weight in enumerate(raw_weights)
        ]
        weight_total = sum(weights)
        if weight_total <= 0:
            raise CalculationError("weights must contain at least one positive value")
        weighted_mean = sum(value * weight for value, weight in zip(values, weights)) / weight_total
        result["weighted_mean"] = _clean(weighted_mean)
        result["weight_total"] = _clean(weight_total)
    return result


def calculate_scenario_forecast(operation: dict[str, Any]) -> dict[str, Any]:
    base = _nonnegative(operation.get("base_value"), "base_value")
    raw_years = operation.get("years")
    if isinstance(raw_years, bool) or not isinstance(raw_years, int) or raw_years <= 0:
        raise CalculationError("years must be a positive integer")
    rates = operation.get("annual_rates")
    if not isinstance(rates, dict) or not rates:
        raise CalculationError("annual_rates must be a non-empty object")

    scenarios: dict[str, Any] = {}
    for name, raw_rate in rates.items():
        if not isinstance(name, str) or not name.strip():
            raise CalculationError("scenario names must be non-empty strings")
        rate = _number(raw_rate, f"annual_rates.{name}")
        if rate <= -1:
            raise CalculationError(f"annual_rates.{name} must be greater than -1")
        values = [_clean(base * ((1.0 + rate) ** year)) for year in range(1, raw_years + 1)]
        scenarios[name] = {
            "annual_rate": _clean(rate),
            "annual_rate_percent": _clean(rate * 100.0),
            "values_by_year": values,
            "final_value": values[-1],
        }
    return {"base_value": _clean(base), "years": raw_years, "scenarios": scenarios}


CALCULATORS = {
    "cagr": calculate_cagr,
    "market_share": calculate_market_share,
    "margin": calculate_margin,
    "product": calculate_product,
    "summary": calculate_summary,
    "scenario_forecast": calculate_scenario_forecast,
}


def calculate_document(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("schema_version") != "1.0":
        raise CalculationError("schema_version must be '1.0'")
    operations = document.get("operations")
    if not isinstance(operations, list) or not operations:
        raise CalculationError("operations must be a non-empty list")

    results: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise CalculationError(f"operations[{index}] must be an object")
        operation_id = operation.get("id")
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise CalculationError(f"operations[{index}].id must be a non-empty string")
        if operation_id in ids:
            raise CalculationError(f"duplicate operation id: {operation_id}")
        ids.add(operation_id)
        operation_type = operation.get("type")
        if not isinstance(operation_type, str):
            raise CalculationError(f"operation {operation_id}.type must be a string")
        calculator = CALCULATORS.get(operation_type)
        if calculator is None:
            supported = ", ".join(sorted(CALCULATORS))
            raise CalculationError(
                f"operation {operation_id} has unsupported type {operation_type!r}; supported: {supported}"
            )
        try:
            result = calculator(operation)
        except CalculationError as exc:
            raise CalculationError(f"operation {operation_id}: {exc}") from exc
        inputs = {key: value for key, value in operation.items() if key not in {"id", "type"}}
        results.append({"id": operation_id, "type": operation_type, "input": inputs, "result": result})
    return {"schema_version": "1.0", "results": results}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 calculations JSON")
    parser.add_argument("-o", "--output", type=Path, help="write results to this JSON file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        document = json.loads(args.input.read_text(encoding="utf-8-sig"))
        if not isinstance(document, dict):
            raise CalculationError("input root must be an object")
        output = calculate_document(document)
    except (OSError, json.JSONDecodeError, CalculationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
