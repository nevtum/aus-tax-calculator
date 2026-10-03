"""Tests for FY 2025-26 resident income tax (ATO figures, excl. Medicare)."""

import pytest

from tax_calculator import (
    calculate_detailed,
    calculate_from_components,
    calculate_tax,
    effective_rate,
    marginal_rate,
)


@pytest.mark.parametrize(
    "income,expected",
    [
        (0, 0.0),
        (18_200, 0.0),
        (18_201, 0.16),
        (35_000, round((35_000 - 18_200) * 0.16, 2)),  # 2,688.00
        (45_000, 4_288.0),
        (45_001, 4_288.30),
        (60_000, 8_788.0),  # 4,288 + 15,000 × 0.30
        (95_000, 19_288.0),  # 4,288 + 50,000 × 0.30
        (135_000, 31_288.0),
        (135_001, 31_288.37),
        (190_000, 51_638.0),
        (190_001, 51_638.45),
        (300_000, 101_138.0),
    ],
)
def test_calculate_tax_against_ato_figures(income, expected):
    assert calculate_tax(income) == pytest.approx(expected)


@pytest.mark.parametrize(
    "income,expected",
    [
        (0, 0.0),
        (18_200, 0.0),
        (18_201, 0.16),
        (45_000, 0.16),
        (45_001, 0.30),
        (135_000, 0.30),
        (135_001, 0.37),
        (190_000, 0.37),
        (190_001, 0.45),
    ],
)
def test_marginal_rate(income, expected):
    assert marginal_rate(income) == expected


def test_effective_rate_is_total_over_income():
    assert effective_rate(0) == 0.0
    assert effective_rate(60_000) == pytest.approx(8_788 / 60_000)
    assert effective_rate(95_000) == pytest.approx(19_288 / 95_000)


def test_combined_salary_plus_business_is_pooled():
    combined = calculate_from_components(employment_income=80_000, business_income=15_000)
    assert combined.taxable_income == 95_000
    assert combined.total_tax == pytest.approx(19_288.0)
    assert combined.marginal_rate == pytest.approx(0.30)
    assert combined.average_rate == pytest.approx(19_288 / 95_000)
    assert combined.after_tax_income == pytest.approx(95_000 - 19_288)


def test_deductions_reduce_taxable_income():
    r = calculate_from_components(employment_income=60_000, deductions=10_000)
    assert r.taxable_income == 50_000
    assert r.total_tax == pytest.approx(4_288 + 5_000 * 0.30)


def test_detailed_breakdown_sums_to_total():
    r = calculate_detailed(95_000)
    assert sum(b.tax_in_bracket for b in r.breakdown) == pytest.approx(r.total_tax)
    assert sum(b.taxable_in_bracket for b in r.breakdown) == pytest.approx(95_000)


def test_zero_income_result():
    r = calculate_detailed(0)
    assert (r.total_tax, r.after_tax_income, r.marginal_rate, r.average_rate) == (0.0, 0.0, 0.0, 0.0)


def test_medicare_levy_is_flat_two_percent():
    r = calculate_from_components(employment_income=80_000, business_income=15_000)
    assert r.medicare_levy == pytest.approx(95_000 * 0.02)  # 1,900.00
    assert r.total_payable == pytest.approx(19_288.0 + 1_900.0)  # 21,188.00
    assert calculate_detailed(0).medicare_levy == 0.0


def test_withheld_more_than_tax_gives_refund():
    r = calculate_from_components(employment_income=60_000, tax_withheld=10_000)
    assert r.total_tax == pytest.approx(8_788.0)
    assert r.medicare_levy == pytest.approx(1_200.0)
    assert r.total_payable == pytest.approx(9_988.0)
    assert r.tax_withheld == pytest.approx(10_000.0)
    assert r.estimated_refund == pytest.approx(10_000 - 9_988.0)
    assert r.estimated_payable == 0.0


def test_withheld_less_than_tax_gives_payable():
    r = calculate_from_components(
        employment_income=80_000, business_income=15_000, tax_withheld=15_000
    )
    assert r.total_payable == pytest.approx(21_188.0)
    assert r.estimated_refund == 0.0
    assert r.estimated_payable == pytest.approx(21_188.0 - 15_000)


def test_no_withheld_means_full_amount_payable():
    r = calculate_from_components(employment_income=60_000)
    assert r.tax_withheld == 0.0
    assert r.estimated_refund == 0.0
    assert r.estimated_payable == pytest.approx(9_988.0)


@pytest.mark.parametrize(
    "year,expected_60k,expected_95k",
    [
        ("2024-25", 8_788.0, 19_288.0),  # 16% second bracket
        ("2025-26", 8_788.0, 19_288.0),  # 16% second bracket
        ("2026-27", 8_520.0, 19_020.0),  # 15% second bracket
        ("2027-28", 8_252.0, 18_752.0),  # 14% second bracket
    ],
)
def test_year_selects_rate_table(year, expected_60k, expected_95k):
    assert calculate_tax(60_000, year=year) == pytest.approx(expected_60k)
    assert calculate_tax(95_000, year=year) == pytest.approx(expected_95k)
    r = calculate_from_components(employment_income=60_000, year=year)
    assert r.financial_year == year
    assert r.total_tax == pytest.approx(expected_60k)


def test_default_year_is_2025_26():
    assert calculate_tax(60_000) == pytest.approx(8_788.0)
    assert calculate_from_components(employment_income=60_000).financial_year == "2025-26"


def test_bracket_base_amounts_internally_consistent():
    from tax_calculator import RATES_BY_YEAR

    for year, rates in RATES_BY_YEAR.items():
        brackets = rates.brackets
        assert brackets[0].lower == 0 and brackets[0].base_tax == 0.0
        for prev, cur in zip(brackets, brackets[1:]):
            assert cur.base_tax == pytest.approx(
                prev.base_tax + (cur.lower - prev.lower) * prev.rate
            ), f"{year}: base_tax inconsistent at ${cur.lower:,}"


def test_unsupported_year_rejected():
    with pytest.raises(ValueError):
        calculate_tax(60_000, year="2030-31")


def test_year_spelling_variants_accepted():
    assert calculate_tax(60_000, year="2025/26") == pytest.approx(8_788.0)
    assert calculate_tax(60_000, year="2025-2026") == pytest.approx(8_788.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"employment_income": -1},
        {"business_income": -5},
        {"deductions": -1},
        {"employment_income": float("nan")},
        {"employment_income": float("inf")},
    ],
)
def test_invalid_amounts_rejected(kwargs):
    with pytest.raises((TypeError, ValueError)):
        calculate_from_components(**kwargs)


def test_deductions_cannot_exceed_gross():
    with pytest.raises(ValueError):
        calculate_from_components(employment_income=10_000, deductions=10_001)


def test_non_numeric_rejected():
    with pytest.raises(TypeError):
        calculate_tax("60000")  # type: ignore[arg-type]
