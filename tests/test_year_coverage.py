"""Comprehensive FY 2025-26 vs 2026-27 coverage.

Locks ATO resident rates (excl. offsets/MLS/HELP):
  2025-26: 0% <=18,200; 16% to 45k; 30% to 135k; 37% to 190k; 45% above.
  2026-27: identical except 15% to 45k (Treasury Laws Amendment
           (More Cost of Living Relief) Act 2025).

Medicare levy here is a flat 2% (low-income reduction NOT modelled).
"""

import pytest

from tax_calculator import (
    calculate_detailed,
    calculate_from_components,
    calculate_tax,
    effective_rate,
    marginal_rate,
)

# ---------------------------------------------------------------------------
# Full ATO-threshold tables per year
# ---------------------------------------------------------------------------

EXPECTED_2025_26 = [
    (0, 0.0),
    (18_200, 0.0),
    (18_201, 0.16),
    (35_000, 2_688.00),
    (45_000, 4_288.0),
    (45_001, 4_288.30),
    (60_000, 8_788.0),
    (95_000, 19_288.0),
    (135_000, 31_288.0),
    (135_001, 31_288.37),
    (190_000, 51_638.0),
    (190_001, 51_638.45),
    (250_000, 78_638.0),  # 51,638 + 60,000 x 0.45
    (300_000, 101_138.0),
]

# Derived: base@45k = 26,800 x 0.15 = 4,020; then +27,000 / +20,350 as usual.
EXPECTED_2026_27 = [
    (0, 0.0),
    (18_200, 0.0),
    (18_201, 0.15),
    (35_000, 2_520.00),  # 16,800 x 0.15
    (45_000, 4_020.0),
    (45_001, 4_020.30),
    (60_000, 8_520.0),
    (95_000, 19_020.0),
    (135_000, 31_020.0),
    (135_001, 31_020.37),
    (190_000, 51_370.0),
    (190_001, 51_370.45),
    (250_000, 78_370.0),
    (300_000, 100_870.0),  # 51,370 + 110,000 x 0.45
]


@pytest.mark.parametrize("income,expected", EXPECTED_2025_26)
def test_2025_26_full_threshold_table(income, expected):
    assert calculate_tax(income, year="2025-26") == pytest.approx(expected)


@pytest.mark.parametrize("income,expected", EXPECTED_2026_27)
def test_2026_27_full_threshold_table(income, expected):
    assert calculate_tax(income, year="2026-27") == pytest.approx(expected)


def test_second_bracket_cut_saves_268_above_45k():
    """26,800 x 1pp = $268 flat saving once past $45k; proportional below."""
    for income in (45_000, 60_000, 95_000, 135_000, 190_000, 300_000):
        saving = calculate_tax(income, year="2025-26") - calculate_tax(
            income, year="2026-27"
        )
        assert saving == pytest.approx(268.0), income
    # Below the cap the saving scales: e.g. $35k -> 16,800 x 1pp = $168.
    assert calculate_tax(35_000, year="2025-26") - calculate_tax(
        35_000, year="2026-27"
    ) == pytest.approx(168.0)


# ---------------------------------------------------------------------------
# Marginal / effective rates are year-aware
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "income,expected_2526,expected_2627",
    [
        (0, 0.0, 0.0),
        (18_200, 0.0, 0.0),
        (18_201, 0.16, 0.15),
        (35_000, 0.16, 0.15),
        (45_000, 0.16, 0.15),
        (45_001, 0.30, 0.30),
        (135_001, 0.37, 0.37),
        (190_001, 0.45, 0.45),
    ],
)
def test_marginal_rate_both_years(income, expected_2526, expected_2627):
    assert marginal_rate(income, year="2025-26") == expected_2526
    assert marginal_rate(income, year="2026-27") == expected_2627


@pytest.mark.parametrize(
    "income", [0, 18_200, 18_201, 35_000, 45_000, 60_000, 95_000, 135_000, 190_000, 300_000]
)
def test_effective_rate_matches_tax_over_income_both_years(income):
    for year in ("2025-26", "2026-27"):
        expected = 0.0 if income == 0 else calculate_tax(income, year=year) / income
        assert effective_rate(income, year=year) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Detailed results per year (tax + flat 2% levy + take-home semantics)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "year,tax_60k,payable_60k,tax_95k,payable_95k",
    [
        ("2025-26", 8_788.0, 9_988.0, 19_288.0, 21_188.0),
        ("2026-27", 8_520.0, 9_720.0, 19_020.0, 20_920.0),
    ],
)
def test_total_payable_is_tax_plus_2pc_levy(year, tax_60k, payable_60k, tax_95k, payable_95k):
    r60 = calculate_detailed(60_000, year=year)
    assert (r60.total_tax, r60.medicare_levy, r60.total_payable) == pytest.approx(
        (tax_60k, 1_200.0, payable_60k)
    )
    assert r60.financial_year == year
    r95 = calculate_detailed(95_000, year=year)
    assert (r95.total_tax, r95.medicare_levy, r95.total_payable) == pytest.approx(
        (tax_95k, 1_900.0, payable_95k)
    )
    # Breakdowns reconcile and cover the full taxable income.
    for r, income in ((r60, 60_000), (r95, 95_000)):
        assert sum(b.tax_in_bracket for b in r.breakdown) == pytest.approx(r.total_tax)
        assert sum(b.taxable_in_bracket for b in r.breakdown) == pytest.approx(income)


@pytest.mark.parametrize("year", ["2025-26", "2026-27"])
def test_after_tax_income_excludes_levy_by_design(year):
    """Current contract: after_tax = taxable - income tax (levy reported
    separately via total_payable). Locked here so any change is deliberate."""
    r = calculate_detailed(60_000, year=year)
    assert r.after_tax_income == pytest.approx(60_000 - r.total_tax)
    assert r.total_payable == pytest.approx(r.total_tax + r.medicare_levy)


@pytest.mark.parametrize("year", ["2025-26", "2026-27"])
def test_zero_and_fully_deducted_income(year):
    for r in (
        calculate_detailed(0, year=year),
        calculate_from_components(
            employment_income=50_000, deductions=50_000, year=year
        ),
    ):
        assert r.taxable_income == 0.0
        assert r.total_tax == 0.0
        assert r.medicare_levy == 0.0
        assert r.total_payable == 0.0
        assert r.marginal_rate == 0.0
        assert r.average_rate == 0.0


# ---------------------------------------------------------------------------
# Components / withholding per year
# ---------------------------------------------------------------------------

def test_business_only_pooled_2026_27():
    r = calculate_from_components(business_income=95_000, year="2026-27")
    assert r.taxable_income == 95_000
    assert r.total_tax == pytest.approx(19_020.0)
    assert r.total_payable == pytest.approx(20_920.0)
    assert r.marginal_rate == pytest.approx(0.30)


def test_deductions_can_pull_across_bracket_2026_27():
    # $50k gross -> $40k taxable drops $5k of 30% income; tax = 15% slice only.
    r = calculate_from_components(
        employment_income=50_000, deductions=10_000, year="2026-27"
    )
    assert r.taxable_income == 40_000
    assert r.total_tax == pytest.approx((40_000 - 18_200) * 0.15)


def test_withheld_exact_balance_both_years():
    for year, payable in (("2025-26", 9_988.0), ("2026-27", 9_720.0)):
        r = calculate_from_components(
            employment_income=60_000, tax_withheld=payable, year=year
        )
        assert r.total_payable == pytest.approx(payable)
        assert r.estimated_refund == 0.0
        assert r.estimated_payable == 0.0


def test_withheld_refund_path_2026_27():
    r = calculate_from_components(
        employment_income=60_000, tax_withheld=10_000, year="2026-27"
    )
    assert r.total_payable == pytest.approx(9_720.0)
    assert r.estimated_refund == pytest.approx(280.0)
    assert r.estimated_payable == 0.0


def test_fractional_dollar_rounds_to_cents_both_years():
    # 50c into the second bracket, rounded to cents (Python round-half-even
    # on the binary float: 0.5*0.16 -> 0.08, 0.5*0.15 -> 0.07).
    assert calculate_tax(18_200.50, year="2025-26") == pytest.approx(0.08)
    assert calculate_tax(18_200.50, year="2026-27") == pytest.approx(0.07)


# ---------------------------------------------------------------------------
# Validation applies regardless of year
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("year", ["2025-26", "2026-27"])
@pytest.mark.parametrize("bad", [-1, -0.01, float("nan"), float("inf")])
def test_bad_taxable_rejected_both_years(year, bad):
    with pytest.raises((TypeError, ValueError)):
        calculate_tax(bad, year=year)
    with pytest.raises((TypeError, ValueError)):
        marginal_rate(bad, year=year)
    with pytest.raises((TypeError, ValueError)):
        effective_rate(bad, year=year)


@pytest.mark.parametrize("year", ["2025-26", "2026-27", "2025/26", "2026/27"])
def test_year_spelling_variants_both_years(year):
    base = "2025-26" if "2025" in year else "2026-27"
    assert calculate_tax(60_000, year=year) == pytest.approx(
        calculate_tax(60_000, year=base)
    )
