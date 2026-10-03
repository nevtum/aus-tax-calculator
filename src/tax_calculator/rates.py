"""Australian resident individual income tax rates, multi-year table.

Sources: ATO resident rates; Treasury Laws Amendment (More Cost of Living
Relief) Act 2025 (legislated the 15% rate for 2026-27 and 14% for 2027-28).
All years below exclude Medicare levy/surcharge/offsets from the *brackets*;
the flat 2% Medicare levy is applied separately in the calculator.

What typically changes year to year (and where each lives in this codebase):
  - Bracket rates / thresholds / base amounts -> YearRates.brackets below.
  - Medicare levy rate / low-income thresholds -> medicare_levy_rate below
    (low-income reduction NOT modelled; flat rate is exact above the
    shade-out: singles $35,013 in 2025-26, higher for families/seniors).
  - Offsets (e.g. LITO/LMITO), MLS tiers, HELP repayment thresholds ->
    not modelled yet; they would become extra fields on YearRates.
"""

from dataclasses import dataclass
from typing import Optional

TAX_FREE_THRESHOLD = 18_200


@dataclass(frozen=True)
class Bracket:
    lower: int  # inclusive lower bound of taxable income in this slice
    upper: Optional[int]  # inclusive upper bound, None = no cap
    rate: float  # marginal rate as decimal, e.g. 0.16
    base_tax: float  # tax payable at `lower` (i.e. cumulative tax below bracket)


# Medicare levy default: flat 2% of taxable income. This is exact for
# taxpayers above the low-income shade-out (singles: $35,013 in 2025-26;
# higher for families / seniors). The low-income reduction (nil ≤ $28,011
# singles, 10%-of-excess shade-in above that) and exemptions are NOT
# modelled — see calculator.
DEFAULT_MEDICARE_LEVY_RATE = 0.02


def _stage3_brackets(second_rate: float) -> tuple[Bracket, ...]:
    """Build the standard post-2024 brackets for a $18,201–$45,000 rate.

    Only the second-bracket rate has moved in recent years (16% -> 15% ->
    14%); the other brackets are unchanged, so each year's base amounts
    derive from it:
      base@$45k  = 26,800 × second_rate
      base@$135k = base@$45k + 90,000 × 0.30
      base@$190k = base@$135k + 55,000 × 0.37
    """
    base_45k = round(26_800 * second_rate, 2)
    base_135k = round(base_45k + 90_000 * 0.30, 2)
    base_190k = round(base_135k + 55_000 * 0.37, 2)
    return (
        Bracket(lower=0, upper=18_200, rate=0.0, base_tax=0.0),
        Bracket(lower=18_200, upper=45_000, rate=second_rate, base_tax=0.0),
        Bracket(lower=45_000, upper=135_000, rate=0.30, base_tax=base_45k),
        Bracket(lower=135_000, upper=190_000, rate=0.37, base_tax=base_135k),
        Bracket(lower=190_000, upper=None, rate=0.45, base_tax=base_190k),
    )


@dataclass(frozen=True)
class YearRates:
    """Everything about the tax year that can change year to year."""

    financial_year: str  # e.g. "2025-26"
    income_year: str  # e.g. "1 July 2025 – 30 June 2026"
    brackets: tuple[Bracket, ...]
    medicare_levy_rate: float = DEFAULT_MEDICARE_LEVY_RATE


# To add a new financial year: add one line here (plus tests). Nothing else
# needs to change — the calculator and CLI select via `year`.
RATES_BY_YEAR: dict[str, YearRates] = {
    "2024-25": YearRates("2024-25", "1 July 2024 – 30 June 2025",
                         _stage3_brackets(0.16)),
    "2025-26": YearRates("2025-26", "1 July 2025 – 30 June 2026",
                         _stage3_brackets(0.16)),
    "2026-27": YearRates("2026-27", "1 July 2026 – 30 June 2027",
                         _stage3_brackets(0.15)),
    "2027-28": YearRates("2027-28", "1 July 2027 – 30 June 2028",
                         _stage3_brackets(0.14)),
}

SUPPORTED_YEARS: tuple[str, ...] = tuple(RATES_BY_YEAR)
DEFAULT_YEAR = "2025-26"

# Backwards-compatible aliases for the default year.
FINANCIAL_YEAR = DEFAULT_YEAR
BRACKETS: tuple[Bracket, ...] = RATES_BY_YEAR[DEFAULT_YEAR].brackets
MEDICARE_LEVY_RATE = RATES_BY_YEAR[DEFAULT_YEAR].medicare_levy_rate


def get_rates(year: str) -> YearRates:
    """Return the YearRates for a year like "2025-26" ("2025/26" also works)."""
    key = year.strip().replace("/", "-")
    parts = key.split("-")
    if len(parts) == 2 and len(parts[1]) == 4:  # "2025-2026" -> "2025-26"
        key = f"{parts[0]}-{parts[1][2:]}"
    try:
        return RATES_BY_YEAR[key]
    except KeyError:
        raise ValueError(
            f"unsupported financial year {year!r}; "
            f"supported: {', '.join(SUPPORTED_YEARS)}"
        ) from None
