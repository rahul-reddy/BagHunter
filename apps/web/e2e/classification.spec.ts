import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('mature multibagger counts retain unavailable attempts and never become probability forecasts', async ({page}) => {
  await page.goto('/');await page.getByRole('button',{name:'Validation Lab',exact:true}).click();
  const panel = page.getByRole('region',{name:'Frozen multibagger classification',exact:true});
  await expect(panel).toContainText('96 retained attempts');
  const table = panel.getByRole('table',{name:'Frozen-budget classification comparisons',exact:true});
  await expect(table.getByRole('row')).toHaveCount(4);
  await expect(panel).toContainText('Calibration is unavailable: rank scores are not probabilities.');
  await panel.getByLabel('Classification horizon',{exact:true}).selectOption('5');
  await expect(table.getByRole('row').nth(1).getByRole('cell').nth(3)).toHaveText('Unavailable');
  await expect(panel.getByRole('table',{name:'Classification anchor evidence and missing outcomes',exact:true})).toContainText('Horizon has not matured');
  await panel.getByLabel('Classification horizon',{exact:true}).selectOption('1');
  await panel.getByLabel('Classification family to inspect',{exact:true}).selectOption('seeded_random');
  const pending = page.waitForEvent('download');
  await panel.getByRole('link',{name:'Download every classification attempt',exact:true}).click();
  const chunks: Buffer[] = [];for await (const part of (await (await pending).createReadStream())!) chunks.push(Buffer.from(part));
  const report = JSON.parse(Buffer.concat(chunks).toString());
  const run = await (await page.request.get('/api/runs/current')).json();
  expect(report).toEqual(run.validation.classification);
  expect(report.dataset_sha256).toBe(run.sources[0].sha256);
  expect(report.selector_policy_sha256).toBe(run.discovery.policy_sha256);
  expect(report.attempts).toHaveLength(96);expect(report.calibration.brier_score).toBeNull();
  expect(report.attempts.some((row:{status:string}) => row.status === 'HORIZON_NOT_MATURED')).toBe(true);
  expect(report.summaries.every((row:{uncertainty:{precision_interval_95:unknown}}) => row.uncertainty.precision_interval_95 === null)).toBe(true);
  const summary = await page.request.get(`/api/runs/${run.run_id}/reports/classification.md`);
  expect(summary.status()).toBe(200);expect(await summary.text()).toContain(run.run_id);
  await panel.getByText('Classification definitions, source binding and exclusions',{exact:true}).click();
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  await page.setViewportSize({width:390,height:844});
  await panel.getByRole('region',{name:'Scrollable classification comparisons',exact:true}).focus();
  await expect(panel.getByRole('region',{name:'Scrollable classification comparisons',exact:true})).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
});

test('legacy classification remains unavailable instead of recomputing under new code', async ({page,request}) => {
  const run = await (await request.get('/api/runs/current')).json();
  delete run.validation.classification;
  await page.route('**/api/runs/current',route => route.fulfill({json:run}));
  await page.goto('/');await page.getByRole('button',{name:'Validation Lab',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Multibagger classification unavailable',exact:true})).toBeVisible();
  await expect(page.getByRole('link',{name:'Download every classification attempt',exact:true})).toHaveCount(0);
});
