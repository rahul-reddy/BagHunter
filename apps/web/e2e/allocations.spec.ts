import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('allocation comparison targets, risk clocks, sector drift and cash are inspectable', async ({page}) => {
  const run = await (await page.request.get('/api/runs/current')).json();
  const report = await page.request.get(`/api/runs/${run.run_id}/reports/portfolio_comparators.json`);
  expect(report.status()).toBe(200);
  expect(await report.json()).toEqual(run.portfolio.comparator_runs);
  expect(run.portfolio.comparator_runs).toHaveLength(7);
  await page.goto('/');
  await page.getByRole('button', {name: 'Validation Lab', exact:true}).click();
  const panel = page.getByRole('region', {name:'Allocation comparisons', exact:true});
  await expect(panel.getByRole('table', {name:'Ranking and allocation comparisons'})).toBeVisible();
  await panel.getByRole('combobox', {name:'Inspect allocation comparison', exact:true}).selectOption('momentum_63d__inverse_volatility');
  await expect(panel.getByRole('table', {name:'Dated allocation targets'})).toContainText('60 returns');
  const risk = run.portfolio.comparator_runs.find((c: {id:string}) => c.id === 'momentum_63d__inverse_volatility');
  const last = risk.allocation_ledger.at(-1).decision;
  await panel.getByRole('combobox', {name:'Allocation decision', exact:true}).selectOption(last);
  await expect(panel.getByRole('status')).toContainText(last);
  await panel.getByRole('combobox', {name:'Inspect allocation comparison', exact:true}).selectOption('momentum_63d__sector_neutral');
  await expect(panel.getByRole('table', {name:'Requested and realized sector weights'})).toBeVisible();
  await panel.getByText('Allocation definitions and limitations', {exact:true}).click();
  await expect(panel.getByText(/whole-share rounding leave cash/)).toBeVisible();
  await panel.getByRole('combobox', {name:'Inspect allocation comparison', exact:true}).selectOption('momentum_63d__cash');
  await expect(panel.getByRole('status')).toContainText('100.00%');
  await expect(panel.getByRole('table', {name:'Dated allocation targets'})).toContainText('Cash allocation');
  await expect(panel.getByRole('link', {name:'Download allocation comparison ledgers'})).toHaveAttribute('href', `/api/runs/${run.run_id}/reports/portfolio_comparators.json`);
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  await page.setViewportSize({width:390,height:844});
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('legacy allocation archives preserve their summary without inventing target ledgers', async ({page}) => {
  await page.route('**/api/runs/current', async route => {
    const run = await (await route.fetch()).json();
    delete run.portfolio.comparator_runs;
    run.portfolio.comparators = run.portfolio.comparators.slice(0,3);
    await route.fulfill({json:run});
  });
  await page.goto('/');
  await page.getByRole('button', {name:'Validation Lab',exact:true}).click();
  await expect(page.getByText(/Allocation comparison ledgers unavailable/)).toBeVisible();
  await expect(page.getByRole('table', {name:'Constrained baseline comparisons'})).toBeVisible();
  await expect(page.getByRole('combobox', {name:'Inspect allocation comparison', exact:true})).toHaveCount(0);
});
