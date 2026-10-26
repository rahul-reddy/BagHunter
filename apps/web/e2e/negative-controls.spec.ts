import {test, expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('negative controls show frozen dated windows, null diagnostics and reproducible export', async ({page}) => {
  test.setTimeout(60_000);
  await page.goto('/');
  await page.getByRole('button', {name: 'Validation Lab', exact: true}).click();
  const panel = page.getByRole('region', {name: 'Negative-control diagnostics', exact: true});
  await expect(panel.getByRole('heading', {name: 'Negative controls', exact: true})).toBeVisible();
  await expect(panel).toContainText('12 testable windows');
  await expect(panel).toContainText('30 candidate observations');
  await expect(panel).toContainText('not a p-value');
  const table = panel.getByRole('table', {name: 'Frozen ranking and negative-control comparisons', exact: true});
  await expect(table).toContainText('Date-balanced peer base rate');
  await expect(table).toContainText('Predated irrelevant rank');
  const select = panel.getByLabel('Negative-control decision window', {exact: true});
  const values = await select.locator('option').allTextContents();
  await select.selectOption(values.at(-1)!);
  await expect(panel).toContainText(`Signal ${values.at(-1)}`);
  const pending = page.waitForEvent('download');
  await panel.getByRole('link', {name: 'Download negative-control report', exact: true}).click();
  const download = await pending;
  expect(download.suggestedFilename()).toBe('discovery_negative_controls.json');
  const parts: Buffer[] = []; const stream = await download.createReadStream();
  for await (const chunk of stream!) parts.push(Buffer.from(chunk));
  const data = JSON.parse(Buffer.concat(parts).toString());
  expect(data.selector_model).toBe('discovery-v1-unvalidated');
  expect(data.selector_config_sha256).toMatch(/^[a-f0-9]{64}$/);
  await panel.getByLabel('Negative-control ranking', {exact: true}).selectOption('momentum');
  await expect(panel).toContainText('frozen-63d-momentum-v0');
  await panel.getByLabel('Negative-control ranking', {exact: true}).selectOption('discovery');
  expect(data.policy).toBe('date-local-negative-controls-v1');
  expect(data.window_details).toHaveLength(12);
  expect(data.input_sha256).toMatch(/^[a-f0-9]{64}$/);
  expect(data.window_details.every((row: {irrelevant_feature_at: string; decision: string; label_available_at: string}) => row.irrelevant_feature_at < row.decision && Date.parse(row.label_available_at) <= Date.parse(data.asof))).toBe(true);
  await panel.getByText('Negative-control policy and limitations', {exact: true}).click();
  await expect(panel).toContainText(data.input_sha256);
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
});

test('legacy missing controls and out-of-range financial ratios remain explicit', async ({page}) => {
  await page.route('**/api/runs/current', async route => {
    const response = await route.fetch(); const data = await response.json();
    delete data.validation.negative_controls;
    delete data.validation.discovery_negative_controls;
    for (const signal of data.signals) signal.financials = {...signal.financials, revenue_growth: null, numeric_limits: ['revenue_growth']};
    await route.fulfill({json: data});
  });
  await page.goto('/');
  await page.getByRole('button', {name: 'Validation Lab', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Negative controls unavailable', exact: true})).toBeVisible();
  await page.getByRole('button', {name: 'Candidate DNA', exact: true}).click();
  await expect(page.getByText('Financial arithmetic outside supported numeric range:', {exact: false})).toContainText('Affected values remain missing');
});
