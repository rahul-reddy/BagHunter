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
  await page.goto('/');
  await page.getByRole('button', { name: 'Finviz Observations', exact: true }).click();
  await expect(page.getByText('<script>fictional company</script>')).toBeVisible();
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
