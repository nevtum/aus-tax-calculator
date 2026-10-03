# Australian Tax Calculator (`aus-tax`)

Calculates Australian **resident individual income tax** for a given financial year,
plus a flat **2% Medicare levy**, from salary/wages, sole-trader business profit,
deductions, and PAYG already withheld.

> Educational tool only — not tax advice. For real lodgments, check the
> [ATO](https://www.ato.gov.au/tax-rates-and-codes/individual-income-tax-rates)
> and see a registered tax agent.

## Tax rates applied

Resident rates (excluding Medicare), per ATO + *Treasury Laws Amendment
(More Cost of Living Relief) Act 2025*:

| Taxable income | 2024-25 | 2025-26 (default) | 2026-27 | 2027-28 |
| --- | --- | --- | --- | --- |
| $0 – $18,200 | Nil | Nil | Nil | Nil |
| $18,201 – $45,000 | 16% | 16% | **15%** | **14%** |
| $45,001 – $135,000 | 30% | 30% | 30% | 30% |
| $135,001 – $190,000 | 37% | 37% | 37% | 37% |
| $190,001+ | 45% | 45% | 45% | 45% |

Medicare levy is modelled as a **flat 2% of taxable income**. This is exact
above the low-income shade-out (singles $35,013 in 2025-26; higher for
families/seniors). The low-income reduction, exemptions, surcharge (MLS),
offsets (e.g. LITO/LMITO), and HELP repayments are **not modelled**.

Sole-trader business profit is pooled with salary at individual marginal
rates — there is no separate business schedule for unincorporated businesses.

## Requirements

- Python ≥ 3.9
- No runtime dependencies (stdlib only). Dev/tests: `pytest`.

## Install & run

```bash
# with uv (repo already has uv.lock)
uv sync
uv run aus-tax --salary 95000 --year 2025-26

# or with the venv directly
.venv/bin/python -m tax_calculator.cli --salary 80000 --business 15000 --deductions 5000 --withheld 15000 --year 2025-26

# interactive prompts
aus-tax --interactive

# machine-readable output
aus-tax --salary 95000 --json
```

Example output (`--salary 95000 --year 2025-26`):

```text
Australian income tax 2025-26 (resident, incl. 2% Medicare levy)
  Taxable income:    $95,000.00
  Income tax:        $19,288.00
  Medicare levy (2%): $1,900.00
  Total payable:     $21,188.00
  After-tax income:  $75,712.00
  Marginal rate:     30%
  Average (effective) rate: 20.30%
```

## Use as a library

```python
from tax_calculator import calculate_tax, calculate_from_components, marginal_rate

calculate_tax(95_000)                              # 19288.0 (default year 2025-26)
calculate_tax(95_000, year="2026-27")              # 19020.0
marginal_rate(95_000, year="2025-26")              # 0.30

result = calculate_from_components(
    employment_income=80_000,
    business_income=15_000,
    deductions=0,
    tax_withheld=15_000,
    year="2025-26",
)
print(result.total_tax)         # income tax excl. Medicare
print(result.medicare_levy)     # flat 2%
print(result.total_payable)     # tax + levy
print(result.estimated_refund)  # withheld - payable (if positive)
print(result.estimated_payable) # payable - withheld (if positive)
```

## Development

```bash
.venv/bin/python -m pytest -q
```

To add a new financial year, add a `RatesXXXX_XX` class in
`src/tax_calculator/rates.py` plus tests — the calculator and CLI pick it up
via the `year` argument.

## Project layout

```text
src/tax_calculator/
  rates.py       # YearRates tables (the only file that changes per Budget)
  calculator.py  # pooling, bracket maths, levy, withholding reconciliation
  cli.py         # aus-tax command (flags, --interactive, --json)
tests/
  test_calculator.py    # ATO figures, components, withholding, validation
  test_year_coverage.py # full threshold tables for 2025-26 vs 2026-27
```
