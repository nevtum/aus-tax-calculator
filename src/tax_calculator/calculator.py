"""Core income-tax calculation for Australian residents (multi-year).

Sole-trader business profit is taxed at the same individual marginal rates,
so employment + business income are pooled into one taxable income figure.
Pass `year="2026-27"` (etc.) to calculate for a different financial year;
supported years live in `.rates.RATES_BY_YEAR`.
"""

from dataclasses import dataclass
from typing import Optional

from .rates import FINANCIAL_YEAR, get_rates

__all__ = [
    "BracketBreakdown",
    "TaxResult",
    "calculate_tax",
    "calculate_detailed",
    "calculate_from_components",
    "marginal_rate",
    "effective_rate",
]


@dataclass(frozen=True)
class BracketBreakdown:
    lower: int
    upper: Optional[int]
    rate: float
    taxable_in_bracket: float
    tax_in_bracket: float


@dataclass(frozen=True)
class TaxResult:
    financial_year: str
    employment_income: float
    business_income: float
    deductions: float
    taxable_income: float
    total_tax: float
    after_tax_income: float
    marginal_rate: float
    average_rate: float  # == effective rate; kept as alias-friendly name
    breakdown: tuple[BracketBreakdown, ...]
    tax_withheld: float = 0.0  # PAYG withheld / prepaid credits already paid
    medicare_levy: float = 0.0  # flat 2% of taxable income (see rates.py)
    total_payable: float = 0.0  # income tax + Medicare levy
    estimated_refund: float = 0.0  # > 0 means money back to you
    estimated_payable: float = 0.0  # > 0 means amount you still owe

    @property
    def effective_rate(self) -> float:
        return self.average_rate


def _validate_amount(name: str, value: float) -> float:
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
    if value != value or value in (float("inf"), float("-inf")):  # NaN / inf
        raise ValueError(f"{name} must be finite, got {value!r}")
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value!r}")
    return float(value)


def marginal_rate(taxable_income: float, year: str = FINANCIAL_YEAR) -> float:
    """Return the marginal (last-dollar) rate for a taxable income and year."""
    income = _validate_amount("taxable_income", taxable_income)
    for b in get_rates(year).brackets:
        if b.upper is None or income <= b.upper:
            return b.rate
    raise AssertionError("unreachable")  # pragma: no cover


def effective_rate(taxable_income: float, year: str = FINANCIAL_YEAR) -> float:
    """Return total income tax / taxable income (0.0 when income is 0)."""
    income = _validate_amount("taxable_income", taxable_income)
    if income == 0:
        return 0.0
    return calculate_tax(income, year=year) / income


def calculate_tax(taxable_income: float, year: str = FINANCIAL_YEAR) -> float:
    """Calculate income tax payable (excl. Medicare) for an income and year."""
    income = _validate_amount("taxable_income", taxable_income)
    for b in get_rates(year).brackets:
        if b.upper is None or income <= b.upper:
            return round(b.base_tax + (income - b.lower) * b.rate, 2)
    raise AssertionError("unreachable")  # pragma: no cover


def calculate_detailed(
    taxable_income: float, year: str = FINANCIAL_YEAR
) -> TaxResult:
    """Full breakdown for a single taxable income figure and year."""
    return calculate_from_components(employment_income=taxable_income, year=year)


def calculate_from_components(
    employment_income: float = 0.0,
    business_income: float = 0.0,
    deductions: float = 0.0,
    tax_withheld: float = 0.0,
    year: str = FINANCIAL_YEAR,
) -> TaxResult:
    """Combine salary/wages + sole-trader business profit less deductions.

    All components are pooled because Australia taxes sole-trader business
    profit at individual marginal rates — there is no separate business
    schedule for unincorporated businesses.

    ``tax_withheld`` is PAYG already withheld (e.g. by your employer, from
    your income statement) plus any other prepaid credits. It does not
    change the tax payable — it is subtracted from it to estimate the
    return outcome: a refund when withheld exceeds the liability, or an
    amount payable when it falls short.

    ``year`` selects the financial year (e.g. "2025-26"); see
    `.rates.SUPPORTED_YEARS`. Medicare levy is a flat 2% here — exact
    above the low-income shade-out, overstated for low incomes (reduction
    not modelled).
    """
    rates = get_rates(year)
    employment = _validate_amount("employment_income", employment_income)
    business = _validate_amount("business_income", business_income)
    deduct = _validate_amount("deductions", deductions)
    withheld = _validate_amount("tax_withheld", tax_withheld)

    gross = employment + business
    if deduct > gross:
        raise ValueError(
            f"deductions ({deduct:,.2f}) cannot exceed gross income ({gross:,.2f})"
        )
    taxable = gross - deduct

    parts: list[BracketBreakdown] = []
    for b in rates.brackets:
        if taxable <= b.lower:
            parts.append(
                BracketBreakdown(b.lower, b.upper, b.rate, 0.0, 0.0)
            )
            continue
        cap = b.upper if b.upper is not None else taxable
        in_bracket = min(taxable, cap) - b.lower
        parts.append(
            BracketBreakdown(
                b.lower, b.upper, b.rate,
                round(in_bracket, 2), round(in_bracket * b.rate, 2),
            )
        )

    total = calculate_tax(taxable, year=year)
    marg = marginal_rate(taxable, year=year)
    avg = 0.0 if taxable == 0 else total / taxable
    levy = round(taxable * rates.medicare_levy_rate, 2) if taxable else 0.0
    payable = round(total + levy, 2)
    withheld_rounded = round(withheld, 2)
    diff = round(withheld_rounded - payable, 2)  # + = refund, - = payable

    return TaxResult(
        financial_year=rates.financial_year,
        employment_income=employment,
        business_income=business,
        deductions=deduct,
        taxable_income=round(taxable, 2),
        total_tax=total,
        after_tax_income=round(taxable - total, 2),
        marginal_rate=marg,
        average_rate=avg,
        breakdown=tuple(parts),
        tax_withheld=withheld_rounded,
        medicare_levy=levy,
        total_payable=payable,
        estimated_refund=diff if diff > 0 else 0.0,
        estimated_payable=-diff if diff < 0 else 0.0,
    )
