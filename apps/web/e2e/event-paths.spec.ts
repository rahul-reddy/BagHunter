import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('event paths expose dated case/control vectors, later-point scope, missing data and delisting', async ({page}) => {
  const run = await (await page.request.get('/api/runs/current')).json();
  const report = await page.request.get(`/api/runs/${run.run_id}/reports/event_paths.json`);
  expect(await report.json()).toEqual(run.study.event_paths);
  expect(run.study.event_paths.anchors).toHaveLength(17);
  const markdown = await page.request.get(`/api/runs/${run.run_id}/reports/event_paths.md`);
  expect(await markdown.text()).toContain(`Run ${run.run_id}`);
  await page.goto('/');
  await page.getByRole('button',{name:'100-Bagger Museum',exact:true}).click();
  const panel = page.getByRole('region',{name:'Historical event paths',exact:true});
  await expect(panel.getByRole('status')).toContainText('Anchor 2020-01-01: 1 cases / 3 eligible');
  await expect(panel.getByRole('table',{name:'Dated case/control path snapshots'})).toContainText('2019-07-17');
  await panel.getByLabel('Inspect path offset',{exact:true}).selectOption('20');
  await panel.getByText('fx-compound · selected offset +20 · dated evidence',{exact:true}).click();
  const details = panel.locator('details[open]').first();
  await expect(details).toContainText('POST ANCHOR DESCRIPTIVE ONLY');
  const source = details.getByRole('link',{name:/fixture source ledger/}).first();
  await expect(source).toBeVisible();
  expect((await (await page.request.get((await source.getAttribute('href'))!)).json()).mode).toBe('FIXTURE');
  await panel.getByLabel('Path metric',{exact:true}).selectOption('revenue_growth');
  await expect(panel.getByText(/No available values for this path metric/)).toBeVisible();
  await panel.getByLabel('Event anchor',{exact:true}).selectOption('2019-01-01');
  await expect(panel.getByRole('table',{name:'Dated case/control path snapshots'})).toContainText('INSUFFICIENT PRICE HISTORY');
  await expect(panel.getByText(/No matched case\/control pair/)).toBeVisible();
  await panel.getByLabel('Event anchor',{exact:true}).selectOption('2022-04-01');
  await panel.getByLabel('Event cohort member',{exact:true}).selectOption('fx-failure');
  await panel.getByLabel('Path metric',{exact:true}).selectOption('close');
  await panel.getByText('fx-failure · selected offset +20 · dated evidence',{exact:true}).click();
  await expect(panel.locator('details[open]').first()).toContainText('INELIGIBLE AT POINT');
  await expect(panel.locator('details[open]').first()).toContainText('-100.00%');
  await expect(panel.getByRole('link',{name:'Download descriptive event paths'})).toHaveAttribute('href',`/api/runs/${run.run_id}/reports/event_paths.json`);
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  await page.setViewportSize({width:390,height:844});
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('legacy museum archives do not invent event paths', async ({page}) => {
  await page.route('**/api/runs/current',async route=>{
    const run=await (await route.fetch()).json(); delete run.study.event_paths;
    await route.fulfill({json:run});
  });
  await page.goto('/');
  await page.getByRole('button',{name:'100-Bagger Museum',exact:true}).click();
  const panel=page.getByRole('region',{name:'Historical event paths',exact:true});
  await expect(panel.getByText(/Event paths unavailable in this archive/)).toBeVisible();
  await expect(panel.getByLabel('Event anchor',{exact:true})).toHaveCount(0);
});
