# SEC financial statements

Data Quality → choose a saved SEC archive → **Inspect quarterly statements, dilution and balance
sheet**. This reads existing validated sources; no new provider request is made. The optional
read-only endpoint is `GET /sec/bundles/{id}/statements?basis=QUARTER&offset=0&limit=12`.
Supported bases are QUARTER, ANNUAL, YTD_6M, YTD_9M and INSTANT. Results paginate newest periods
first, with a maximum page of 100. JSON exports explicitly contain only the current statement page.

## Source and time policy

The existing archive is fully verified first: original hashes, declared history parts, derived
union and annual normalization. The new `sec-statements-v1` report is calculated separately and
does not rewrite v1/v2 bundles or change the annual normalization contract. Source hashes and
manifest accompany the response. Every selected amount retains its exact concept, unit, start/end,
accession, acceptance, publication upper bound and filing URL. The conservative publication bound
and 24-hour lag apply. Latest revisions use publication, acceptance, then accession order.
Shared research fact ordering also uses acceptance to break publication-bound ties.

Only exact supported US-GAAP entity concepts are interpreted. USD, shares and USD/shares are
separate units. Direct quarter durations are 75–105 days, six-month cumulative 150–210, nine-month
240–300 and annual 330–400 days. Annual amounts require 10-K or 10-K/A; other supported observations
must agree with exact 10-K/10-Q accession metadata. Cumulative figures are not subtracted to invent
quarters; missing Q4, short stubs and unsupported taxonomies remain missing. Instant facts have no
start date. The SEC explains aggregate concepts, units and varying fiscal periods in its
[API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).

Normalization rejects conflicting aliases, nonfinite/nonnumeric amounts and negative share counts.
Unsupported units/forms/periods, missing accession metadata and unavailable filings are counted.
Bounds: 20 MiB per raw input, 100,000 examined concept records, 20,000 normalized facts and 1,000
analysis periods. Exceeding a bound fails rather than truncating coverage.

## Interpretation

- Revenue and weighted diluted-share YoY require one same-basis prior period ending 330–400 days
  earlier, durations within 15 days and a positive prior value. Missing or ambiguous prior periods
  stay unavailable. Weighted diluted shares are period averages, not class shares or proof of
  ownership dilution. No historical share prices or market caps are reconstructed.
- Margins require numerator and revenue from the exact same start/end period with positive revenue.
  Each latest available revision is individually cited; a common filing is not guaranteed.
- CFO less PPE requires same-period cashflow and nonnegative payments for property, plant and
  equipment from the same filing. It is a narrow arithmetic proxy, not standardized free cashflow.
- Assets, liabilities, parent equity, cash, current/noncurrent long-term debt and common shares stay
  separately reported. Missing components are never filled with zero or called total debt.
- Original extraction vintages, common-share identity and class-level applicability remain
  unverified. These descriptive reports do not activate predictors, ranking or empirical backtests.

Executed against the existing real history archive: 2,172 statement facts, 55 direct-quarter
periods, 19 annual, 18 six-month cumulative, 19 nine-month cumulative and 76 instant periods.
Zero missing-accession exclusions; 129 unsupported form/period observations. These counts describe
software/source coverage, not investment findings. Tests and release evidence are in STATUS.md.
