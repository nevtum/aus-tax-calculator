"""CLI: aus-tax --payg 80000 --business 20000 [--deductions 5000] [--withheld 20000] [--year 2025-26] [--json].

Or run interactively: aus-tax --interactive (prompts for each value).
"""

import argparse
import json
import sys
from typing import Optional

from .calculator import calculate_from_components
from .rates import DEFAULT_YEAR, SUPPORTED_YEARS


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aus-tax",
        description=(
            "Australian resident income-tax calculator "
            "(income tax + flat 2% Medicare levy; excl. levy reduction, "
            "surcharge, offsets). "
            "Business income is sole-trader profit pooled with salary at "
            "individual marginal rates."
        ),
    )
    p.add_argument("--year", default=DEFAULT_YEAR, choices=SUPPORTED_YEARS,
                   help=f"Financial year (default {DEFAULT_YEAR}).")
    p.add_argument("--salary", "--employment", "--income", "--payg", dest="salary",
                   type=float, default=0.0,
                   help="PAYG salary/wages income (default 0).")
    p.add_argument("--business", "--business-income", dest="business", type=float, default=0.0,
                   help="Sole-trader business profit (default 0).")
    p.add_argument("--deductions", type=float, default=0.0,
                   help="Allowable deductions (default 0).")
    p.add_argument("--withheld", "--tax-withheld", "--payg-withheld", dest="withheld",
                   type=float, default=0.0,
                   help="PAYG tax already withheld (from income statement, default 0).")
    p.add_argument("--json", action="store_true",
                   help="Emit machine-readable JSON.")
    p.add_argument("-i", "--interactive", action="store_true",
                   help="Prompt for each value manually instead of using flags.")
    return p


def _prompt_year(default: str = DEFAULT_YEAR) -> str:
    """Prompt for a financial year; blank keeps the default."""
    from .rates import get_rates  # local import to keep module import light
    while True:
        try:
            raw = input(
                f"Financial year [{default}] ({', '.join(SUPPORTED_YEARS)}): "
            ).strip()
        except EOFError:
            print(file=sys.stderr)
            return default
        if raw == "":
            return default
        try:
            return get_rates(raw).financial_year
        except ValueError as exc:
            print(f"  {exc}", file=sys.stderr)


def _prompt_amount(label: str, default: float = 0.0) -> float:
    """Prompt for a non-negative dollar amount; blank keeps the default."""
    while True:
        try:
            raw = input(f"{label} [{default:,.2f}]: ").strip().replace(",", "").replace("$", "")
        except EOFError:
            print(file=sys.stderr)
            return default
        if raw == "":
            return default
        try:
            value = float(raw)
        except ValueError:
            print(f"  Enter a number (e.g. 80000), or press Enter for {default:,.2f}.",
                  file=sys.stderr)
            continue
        if value < 0:
            print("  Amount must be >= 0.", file=sys.stderr)
            continue
        return value


def format_result(result, *, json_mode: bool = False) -> str:
    if json_mode:
        return json.dumps(
            {
                "financial_year": result.financial_year,
                "employment_income": result.employment_income,
                "business_income": result.business_income,
                "deductions": result.deductions,
                "taxable_income": result.taxable_income,
                "total_tax": result.total_tax,
                "after_tax_income": result.after_tax_income,
                "marginal_rate": result.marginal_rate,
                "average_rate": result.average_rate,
                "tax_withheld": result.tax_withheld,
                "medicare_levy": result.medicare_levy,
                "total_payable": result.total_payable,
                "estimated_refund": result.estimated_refund,
                "estimated_payable": result.estimated_payable,
                "breakdown": [
                    {
                        "lower": b.lower,
                        "upper": b.upper,
                        "rate": b.rate,
                        "taxable_in_bracket": b.taxable_in_bracket,
                        "tax_in_bracket": b.tax_in_bracket,
                    }
                    for b in result.breakdown
                ],
            },
            indent=2,
        )
    lines = [
        f"Australian income tax {result.financial_year} (resident, incl. 2% Medicare levy)",
        f"  Employment income: ${result.employment_income:,.2f}",
        f"  Business income:   ${result.business_income:,.2f}",
        f"  Deductions:        ${result.deductions:,.2f}",
        f"  Taxable income:    ${result.taxable_income:,.2f}",
        "",
        "  Bracket breakdown:",
    ]
    for b in result.breakdown:
        top = f"${b.upper:,}" if b.upper is not None else "no limit"
        lines.append(
            f"    ${b.lower:,}–{top} @ {b.rate:.0%}: "
            f"${b.taxable_in_bracket:,.2f} taxed → ${b.tax_in_bracket:,.2f}"
        )
    lines += [
        "",
        f"  Income tax:        ${result.total_tax:,.2f}",
        f"  Medicare levy (2%): ${result.medicare_levy:,.2f}",
        f"  Total payable:     ${result.total_payable:,.2f}",
        f"  After-tax income:  ${result.after_tax_income:,.2f}",
        f"  Marginal rate:     {result.marginal_rate:.0%}",
        f"  Average (effective) rate: {result.average_rate:.2%}",
    ]
    if result.tax_withheld or result.estimated_refund or result.estimated_payable:
        lines += [
            "",
            f"  Less PAYG withheld:     ${result.tax_withheld:,.2f}",
        ]
        if result.estimated_refund > 0:
            lines.append(f"  Estimated refund:       ${result.estimated_refund:,.2f}")
        elif result.estimated_payable > 0:
            lines.append(f"  Estimated amount payable: ${result.estimated_payable:,.2f}")
        else:
            lines.append("  Balanced exactly — no refund, nothing owing.")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    salary, business, deductions, withheld = args.salary, args.business, args.deductions, args.withheld
    year = args.year
    if args.interactive or (argv is None and len(sys.argv) == 1 and sys.stdin.isatty()):
        year = _prompt_year(year)
        print(f"Australian income tax {year} (resident, incl. 2% Medicare levy)")
        print("Enter GST-exclusive amounts; blank keeps the default shown.")
        salary = _prompt_amount("PAYG salary/wages income", salary)
        business = _prompt_amount("Sole-trader business profit (GST-excl.)", business)
        deductions = _prompt_amount("Allowable deductions", deductions)
        withheld = _prompt_amount("PAYG tax already withheld (income statement)", withheld)
        print()
    try:
        result = calculate_from_components(
            employment_income=salary,
            business_income=business,
            deductions=deductions,
            tax_withheld=withheld,
            year=year,
        )
    except (TypeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(format_result(result, json_mode=args.json))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
