import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir } from 'node:fs/promises';

const id = 'a'.repeat(64);
const manifest = {cik: '0000000001', asof: '2020-04-01T00:00:00Z', status: 'QUARANTINED_SEC_ENTITY_NOT_SECURITY_IDENTITY', lag_hours: 24, submissions: {retrieved_at: '2020-04-02T00:00:00Z'}, companyfacts: {retrieved_at: '2020-04-02T00:00:00Z'}};
const profile = {policy: 'sec-entity-profile-v1', asof: manifest.asof, security_id: 'fixture-entity', periods: 1, status: 'DESCRIPTIVE_ENTITY_FINANCIALS_NOT_SECURITY_RANKING', latest: null, series: [{period_end: '2019-12-31', revenue: 1000000, revenue_growth: null, growth_acceleration: null, operating_margin: .2, net_margin: null, cashflow_margin: .1, citations: [{metric: 'annual_revenue', period_end: '2019-12-31', value: 1000000, unit: 'USD', accession: 'profile-fixture', source_url: 'https://www.sec.gov/Archives/profile-fixture.htm', accepted_at: '2020-02-01T12:00:00Z', published_at: '2020-02-02T00:00:00Z'}]}], limitations: ['Fictional browser fixture']};
const facts = Array.from({length: 10}, (_, i) => ({metric: 'annual_revenue', value: 100+i, unit: 'USD', period_end: `2019-12-${String(i+1).padStart(2, '0')}`, accepted_at: '2020-02-01T12:00:00Z', published_at: '2020-02-02T00:00:00Z', accession: `0000000001-20-${String(i+1).padStart(6, '0')}`, amended: false, source_url: `https://www.sec.gov/Archives/edgar/data/1/000000000120${String(i+1).padStart(6, '0')}/fixture.htm` }));

test('saved SEC evidence remains usable without fixture research and shows source clocks, filters and pages', async ({page}) => {
  test.setTimeout(60_000); // Includes cold Vite compilation, download inspection and accessibility.
  await page.route('**/api/runs/current', route => route.fulfill({status: 503, json: {}}));
  await page.route('**/api/sec/bundles', route => route.fulfill({json: {bundles: [{bundle_id: id, ...manifest}]}}));
  await page.route('**/api/sec/bundles/*?**', route => {
    const params = new URL(route.request().url()).searchParams;
    const offset = Number(params.get('offset'));
    const matching = params.get('metric') === 'annual_net_income' ? [] : facts;
    return route.fulfill({json: {bundle_id: id, manifest, financial_profile: profile, source_facts: 10, total: matching.length, offset, limit: 8, normalized: {normalization_policy: 'sec-annual-v2-publication-day', identity_assignment: 'OPERATOR_SUPPLIED_UNVERIFIED', submission_history: {parts: 1, metadata_rows: 100, usable_metadata_rows: 98, missing_primary_document_rows: 2}, excluded_counts: {missing_accession_metadata: 2}, limitations: ['Fictional test response; no empirical evidence'], facts: matching.slice(offset, offset+8)}}});
  });
  await page.goto('/');
  await page.getByRole('button', {name: 'Data Quality', exact: true}).click();
  await page.getByLabel('Saved SEC evidence', {exact: true}).selectOption(id);
  await expect(page.getByText('Showing 1–8 of 10 SEC facts')).toBeVisible();
  await expect(page.getByText('Processing lag: 24 hours', {exact: false})).toBeVisible();
  await expect(page.getByRole('table', {name: 'Quarantined real SEC annual filing facts'})).toContainText('2020-02-02T00:00:00Z');
  await page.getByRole('button', {name: 'Next SEC facts'}).click();
  await expect(page.getByText('Showing 9–10 of 10 SEC facts')).toBeVisible();
  const pending = page.waitForEvent('download');
  await page.getByRole('button', {name: 'Export current SEC evidence page'}).click();
  const downloaded = await pending;
  expect(downloaded.suggestedFilename()).toBe('SEC-0000000001-page-8.json');
  const stream = await downloaded.createReadStream(); const parts: Buffer[] = [];
  for await (const chunk of stream!) parts.push(Buffer.from(chunk));
  const exported = JSON.parse(Buffer.concat(parts).toString());
  expect(exported.export_scope).toBe('CURRENT_PAGE_ONLY');
  expect(exported.normalized.facts).toHaveLength(2);
  expect(exported.financial_profile).toBeUndefined();
  await expect(page.getByRole('table', {name: 'SEC annual financial profile', exact: true})).toContainText('$1M');
  await page.getByText('Filing citations for 2019-12-31', {exact: true}).click();
  await expect(page.getByRole('link', {name: 'annual_revenue · 2019-12-31 · profile-fixture', exact: true})).toHaveAttribute('href', 'https://www.sec.gov/Archives/profile-fixture.htm');
  await expect(page.getByText('Historical metadata:', {exact: false})).toContainText('2 missing primary documents');
  const profilePending = page.waitForEvent('download');
  await page.getByRole('button', {name: 'Export SEC financial profile', exact: true}).click();
  const profileDownload = await profilePending;
  expect(profileDownload.suggestedFilename()).toBe('SEC-0000000001-financial-profile.json');
  const profileStream = await profileDownload.createReadStream(); const profileParts: Buffer[] = [];
  for await (const chunk of profileStream!) profileParts.push(Buffer.from(chunk));
  expect(JSON.parse(Buffer.concat(profileParts).toString()).financial_profile).toEqual(profile);
  await page.getByLabel('SEC annual metric', {exact: true}).selectOption('annual_net_income');
  await expect(page.getByText('No facts match this metric.')).toBeVisible();
  await expect(page.getByRole('table', {name: 'SEC annual financial profile', exact: true})).toContainText('$1M');
  await page.getByLabel('SEC annual metric', {exact: true}).selectOption('');
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  await mkdir('../../artifacts/screenshots', {recursive: true});
  await page.screenshot({path: '../../artifacts/screenshots/sec-fixture-evidence.png', fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('SEC response source mismatch and verification failure clear the previous facts', async ({page}) => {
  let failure = false;
  await page.route('**/api/sec/bundles', route => route.fulfill({json: {bundles: [{bundle_id: id, ...manifest}]}}));
  await page.route('**/api/sec/bundles/*?**', route => route.fulfill({json: {bundle_id: failure ? 'b'.repeat(64) : id, manifest, source_facts: 1, total: 1, offset: 0, limit: 8, normalized: {normalization_policy: 'test', identity_assignment: 'UNVERIFIED', excluded_counts: {}, limitations: [], facts: facts.slice(0, 1)}}}));
  await page.goto('/');
  await page.getByRole('button', {name: 'Data Quality', exact: true}).click();
  await page.getByLabel('Saved SEC evidence', {exact: true}).selectOption(id);
  await expect(page.getByRole('table', {name: 'Quarantined real SEC annual filing facts'})).toBeVisible();
  failure = true;
  await page.getByRole('button', {name: 'Reload SEC archives'}).click();
  await expect(page.getByRole('alert')).toContainText('does not match the selected archive');
  await expect(page.getByRole('table', {name: 'Quarantined real SEC annual filing facts'})).toHaveCount(0);
});
