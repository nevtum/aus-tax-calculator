"""Australian resident income tax (multi-year; default FY 2025-26)."""

from .calculator import (
    TaxResult,
    calculate_detailed,
    calculate_from_components,
    calculate_tax,
    effective_rate,
    marginal_rate,
)
from .rates import (
    BRACKETS,
    DEFAULT_YEAR,
    FINANCIAL_YEAR,
    MEDICARE_LEVY_RATE,
    RATES_BY_YEAR,
    SUPPORTED_YEARS,
    YearRates,
    get_rates,
)

__all__ = [
    "BRACKETS",
    "DEFAULT_YEAR",
    "FINANCIAL_YEAR",
    "MEDICARE_LEVY_RATE",
    "RATES_BY_YEAR",
    "SUPPORTED_YEARS",
    "TaxResult",
    "YearRates",
    "calculate_detailed",
    "calculate_from_components",
    "calculate_tax",
    "effective_rate",
    "get_rates",
    "marginal_rate",
]
