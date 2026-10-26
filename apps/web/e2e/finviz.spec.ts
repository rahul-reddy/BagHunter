import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir } from 'node:fs/promises';

const observation = (ticker: string, company: string) => ({
  ticker, company, sector: 'Fictional technology', industry: 'Test widgets', country: 'USA',
  market_cap_reported: '123.45', price_reported: null, pe_reported: '0',
  change_fraction: '-0.0125', change_percent_reported: '-1.25', volume_shares: '9223372036854775807', security_id: null, security_type: 'unknown',
});
const coverage = {
  snapshot_id: 'a'.repeat(64), source_sha256: 'b'.repeat(64), mode: 'FIXTURE',
  retrieved_at: '2020-01-01T12:00:01Z', ingested_at: '2020-01-02T12:00:01Z', rows: 51,
  missing: { market_cap_reported: 0, price_reported: 51, change_fraction: 0 }, zero_pe_reported: 51,
  flags: ['FIXTURE_ONLY', 'NO_PIT_HISTORY', 'UNRESOLVED_PERMANENT_IDENTITIES'],
  status: 'QUARANTINED_CURRENT_SNAPSHOT', provider_observation_time: null,
};
const referenceCandidate = (figi = 'BBG000TST001') => ({ figi, ticker: 'DEMO-X', name: 'Fictional reference candidate',
  exchCode: 'US', marketSector: 'Equity', securityType: 'Common Stock', securityType2: 'Common Stock',
  compositeFIGI: figi, shareClassFIGI: 'BBG000TST002' });
const referenceEvidence = { reference_id: 'd'.repeat(64), base_snapshot_id: coverage.snapshot_id,
  mode: 'FIXTURE', retrieved_at: '2020-01-02T12:00:01Z', response_sha256: 'e'.repeat(64),
  queried: 2, population: 51, offset: 0, flags: ['FIXTURE_ONLY', 'CURRENT_REFERENCE_ONLY_NOT_PIT', 'NOT_IDENTITY_PROMOTION'],
  records: [{ ticker: 'DEMO-X', status: 'AMBIGUOUS', candidates: [referenceCandidate(), referenceCandidate('BBG000TST003')], identity_promoted: false },
    { ticker: 'DEMO-Y', status: 'NO_MATCH_REPORTED', candidates: [], identity_promoted: false }],
  reconciliation: { policy_version: 'company-share-class-comparison-v1', report_sha256: 'f'.repeat(64),
    reference_id: 'd'.repeat(64), base_snapshot_id: coverage.snapshot_id, mode: 'FIXTURE',
    flags: ['TEXT_COMPARISON_NOT_IDENTITY_PROOF'], records: [
      { ticker: 'DEMO-X', source_company: '<script>fictional company</script>', disposition: 'REVIEW_REQUIRED',
        candidates: ['BBG000TST001', 'BBG000TST003'].map(figi => ({ figi, name_comparison: 'DIFFERENT_TEXT',
          issues: ['COMPANY_NAME_DIFFERS', 'MISSING_SHARECLASSFIGI'], shared_identifiers: {} })) },
      { ticker: 'DEMO-Y', source_company: 'Imaginary company', disposition: 'NO_CANDIDATE_EVIDENCE', candidates: [] },
    ] } };

test('explicit saved snapshot selection validates source binding without environment setup', async ({page}) => {
  await page.route('**/api/finviz/snapshots', route => route.fulfill({json: {snapshots: [{snapshot_id: coverage.snapshot_id, mode: 'FIXTURE', rows: 51, retrieved_at: coverage.retrieved_at}]}}));
  let mismatch = false;
  await page.route('**/api/finviz/observations?**', route => {
    const selected = new URL(route.request().url()).searchParams.get('snapshot');
    if (!selected) return route.fulfill({status: 503, body: '{}'});
    return route.fulfill({json: {coverage: {...coverage, snapshot_id: mismatch ? 'c'.repeat(64) : coverage.snapshot_id}, age_hours: 100, stale: true, total: 1, offset: 0, limit: 50, observations: [observation('DEMO-X', 'Fictional explicitly selected company')]}});
  });
  await page.goto('/');
  await page.getByRole('button', {name: 'Finviz Observations', exact: true}).click();
  await expect(page.getByRole('alert')).toContainText('Select a valid local Finviz snapshot');
  await page.getByLabel('Saved Finviz snapshot').selectOption(`FIXTURE:${coverage.snapshot_id}`);
  await expect(page.getByText('Fictional explicitly selected company')).toBeVisible();
  mismatch = true;
  await page.getByRole('button', {name: 'Reload snapshot'}).click();
  await expect(page.getByRole('alert')).toContainText('does not match the selected source');
  await expect(page.getByText('Fictional explicitly selected company')).toHaveCount(0);
});

test('Finviz browsing, search, pagination and failure never mix with fixture rankings', async ({ page }) => {
  await page.route('**/api/runs/current', route => route.fulfill({ status: 503, body: '{}' }));
  await page.route('**/api/finviz/observations?**', route => {
    const params = new URL(route.request().url()).searchParams;
    const offset = Number(params.get('offset') ?? 0), q = params.get('q') ?? '';
    const rows = q === 'no-match' ? [] : offset === 0
      ? Array.from({ length: 50 }, (_, i) => observation(`DEMO-${String(i).padStart(2, '0')}`, `Fictional company ${i}`))
      : [observation('DEMO-50', 'Imaginary final company')];
    return route.fulfill({ json: { coverage, age_hours: 100, stale: true, total: q === 'no-match' ? 0 : 51,
      offset, limit: 50, observations: rows } });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Finviz Observations', exact: true }).click();
  await expect(page.getByText('SYNTHETIC FINVIZ TEST FIXTURE')).toBeVisible();
  await expect(page.getByText('Showing 1–50 of 51 observations')).toBeVisible();
  await expect(page.getByText('STALE SNAPSHOT', { exact: false })).toBeVisible();
  await expect(page.getByText('123.45').first()).toBeVisible();
  await expect(page.getByText('Missing', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('-1.25%', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('9223372036854775807', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('0 (reported; unresolved)').first()).toBeVisible();
  await expect(page.getByRole('button', { name: /Score breakdown/ })).toHaveCount(0);
  await page.getByRole('button', { name: 'Next observations' }).click();
  await expect(page.getByText('Showing 51–51 of 51 observations')).toBeVisible();
  await expect(page.getByText('Imaginary final company')).toBeVisible();
  await page.getByLabel('Search Finviz observations').fill('no-match');
  await page.getByRole('button', { name: 'Search observations', exact: true }).click();
  await expect(page.getByText('No observations match this search.')).toBeVisible();
  await page.route('**/api/finviz/observations?**', route => route.fulfill({ status: 503, body: '{}' }));
  await page.getByRole('button', { name: 'Reload snapshot' }).click();
  await expect(page.getByRole('alert')).toContainText('Finviz snapshot unavailable');
  await expect(page.getByText('Imaginary final company')).toHaveCount(0);
});

test('Finviz mobile accessibility, lineage and snapshot label', async ({ page }) => {
  await mkdir('../../artifacts/screenshots', { recursive: true });
  await page.route('**/api/finviz/observations?**', route => route.fulfill({ json: {
    coverage, age_hours: 0.1, stale: false, total: 1, offset: 0, limit: 50,
    observations: [observation('DEMO-X', '<script>fictional company</script>')],
  } }));
  await page.route('**/api/finviz/reference', route => route.fulfill({ json: referenceEvidence }));
  await page.goto('/');
  await page.getByRole('button', { name: 'Finviz Observations', exact: true }).click();
  await expect(page.getByText('<script>fictional company</script>')).toBeVisible();
  await page.getByRole('button', { name: 'Inspect reference evidence' }).click();
  await expect(page.getByText('SYNTHETIC REFERENCE FIXTURE')).toBeVisible();
  await page.getByText('DEMO-X · AMBIGUOUS · 2 candidates', { exact: true }).click();
  await expect(page.getByText('Fictional reference candidate', { exact: false }).first()).toBeVisible();
  await expect(page.getByText('Finviz company: <script>fictional company</script>', { exact: true })).toBeVisible();
  await expect(page.getByText('Name comparison: DIFFERENT TEXT.', { exact: false }).first()).toBeVisible();
  await expect(page.getByText('MISSING SHARECLASSFIGI', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('Disposition: REVIEW REQUIRED.', { exact: false })).toBeVisible();
  await page.getByRole('region', { name: 'Scrollable Finviz observations' }).focus();
  await expect(page.getByRole('region', { name: 'Scrollable Finviz observations' })).toBeFocused();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.screenshot({ path: '../../artifacts/screenshots/finviz-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByText('Source lineage and coverage gaps').click();
  await expect(page.getByText(coverage.source_sha256, { exact: true })).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: '../../artifacts/screenshots/finviz-mobile.png', fullPage: true });
});

test('reference evidence rejects cross-source data, labels external mode and clears errors', async ({ page }) => {
  await page.route('**/api/finviz/observations?**', route => route.fulfill({ json: {
    coverage: { ...coverage, mode: 'EXTERNAL_UNVERIFIED' }, age_hours: 1, stale: false,
    total: 1, offset: 0, limit: 50, observations: [observation('DEMO-X', 'Fictional external-mode test')],
  } }));
  await page.route('**/api/finviz/reference', route => route.fulfill({ json: {
    ...referenceEvidence, mode: 'EXTERNAL_UNVERIFIED', base_snapshot_id: 'c'.repeat(64),
  } }));
  await page.goto('/');
  await page.getByRole('button', { name: 'Finviz Observations', exact: true }).click();
  await page.getByRole('button', { name: 'Inspect reference evidence' }).click();
  await expect(page.getByRole('alert')).toContainText('different source selection');
  await expect(page.getByText('DEMO-X · AMBIGUOUS · 2 candidates', { exact: true })).toHaveCount(0);
  await page.route('**/api/finviz/reference', route => route.fulfill({ json: {
    ...referenceEvidence, mode: 'EXTERNAL_UNVERIFIED',
    reconciliation: { ...referenceEvidence.reconciliation, mode: 'EXTERNAL_UNVERIFIED' },
  } }));
  await page.getByRole('button', { name: 'Inspect reference evidence' }).click();
  await expect(page.getByText('OPENFIGI · CURRENT CANDIDATES', { exact: true })).toBeVisible();
  await page.route('**/api/finviz/reference', route => route.fulfill({ json: {
    ...referenceEvidence, mode: 'EXTERNAL_UNVERIFIED',
    reconciliation: { ...referenceEvidence.reconciliation, mode: 'EXTERNAL_UNVERIFIED', reference_id: '0'.repeat(64) },
  } }));
  await page.getByRole('button', { name: 'Inspect reference evidence' }).click();
  await expect(page.getByRole('alert')).toContainText('Comparison evidence does not match');
  await expect(page.getByText('OPENFIGI · CURRENT CANDIDATES', { exact: true })).toHaveCount(0);
  await page.route('**/api/finviz/reference', route => route.fulfill({ status: 503, body: '{}' }));
  await page.getByRole('button', { name: 'Inspect reference evidence' }).click();
  await expect(page.getByRole('alert')).toContainText('No valid local reference batch');
  await expect(page.getByText('DEMO-X · AMBIGUOUS · 2 candidates', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Fictional external-mode test')).toBeVisible();
});
