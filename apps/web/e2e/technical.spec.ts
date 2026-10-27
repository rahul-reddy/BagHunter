import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('dated technical evidence, source-bound export and mobile access', async ({page}) => {
  const run = await (await page.request.get('/api/runs/current')).json();
  const report = await page.request.get(`/api/runs/${run.run_id}/reports/technical_evidence.json`);
  expect(report.status()).toBe(200);
  const data = await report.json();
  expect(data.run_id).toBe(run.run_id);
  expect(data.signals[0].technical.policy).toBe('technical-evidence-v1');
  await page.goto('/');
  await page.getByRole('button', {name: /Score breakdown for DEMO-A/}).click();
  const panel = page.getByRole('region', {name: 'Technical evidence', exact: true});
  await expect(panel.getByRole('heading', {name: 'Dated technical evidence'})).toBeVisible();
  await expect(panel.getByText('Distance from prior highs', {exact: true})).toBeVisible();
  await expect(panel.getByText('Volatility contraction (20D / 60D)', {exact: true})).toBeVisible();
  await panel.getByText('Formulas, missingness and source clocks', {exact: true}).click();
  await expect(panel.getByText(/population standard deviation/)).toBeVisible();
  await expect(panel.getByRole('link', {name: 'Download dated technical evidence'})).toHaveAttribute('href', `/api/runs/${run.run_id}/reports/technical_evidence.json`);
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  await page.setViewportSize({width: 390, height: 844});
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('legacy technical archive shows missing catalog without replacing it', async ({page}) => {
  await page.route('**/api/runs/current', async route => {
    const run = await (await route.fetch()).json();
    for (const signal of run.signals) {
      delete signal.technical;
      delete signal.relative_evidence;
    }
    await route.fulfill({json: run});
  });
  await page.goto('/');
  await page.getByRole('button', {name: /Score breakdown for DEMO-A/}).click();
  const panel = page.getByRole('region', {name: 'Technical evidence', exact: true});
  await expect(panel.getByText(/Technical catalog unavailable/)).toBeVisible();
  await expect(panel.getByText('Cross-section evidence unavailable in this archive.')).toBeVisible();
  await expect(panel.getByText('Distance from prior highs')).toHaveCount(0);
});
