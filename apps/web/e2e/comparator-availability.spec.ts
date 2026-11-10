import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('Validation Lab retains unavailable annual earnings alongside available comparators',async({page,request})=>{
  const run=await(await request.get('/api/runs/current')).json();
  const catalog=run.portfolio.comparator_catalog;
  expect(catalog.policy).toBe('declared-comparator-catalog-v1');
  expect(catalog.dataset_sha256).toBe(run.sources[0].sha256);
  expect(catalog.attempts).toHaveLength(8);
  const earnings=catalog.attempts.find((a:{policy:{selector:string}})=>a.policy.selector==='earnings_growth');
  expect(earnings.status).toBe('UNAVAILABLE_DATED_ANNUAL_EARNINGS');
  expect(earnings.metrics).toBeNull();
  expect(run.portfolio.comparator_runs).toHaveLength(7);
  await page.goto('/');await page.getByRole('button',{name:'Validation Lab',exact:true}).click();
  const table=page.getByRole('table',{name:'Declared comparator availability',exact:true});
  await expect(table.getByRole('row')).toHaveCount(9);
  await expect(table.getByRole('row').filter({hasText:'earnings_growth'})).toContainText('no revenue proxy or cash return substituted');
  const pending=page.waitForEvent('download');await page.getByRole('link',{name:'Download comparator availability',exact:true}).click();
  const chunks:Buffer[]=[];for await(const part of (await(await pending).createReadStream())!) chunks.push(Buffer.from(part));
  expect(JSON.parse(Buffer.concat(chunks).toString())).toEqual(catalog);
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  await page.setViewportSize({width:390,height:844});
  const scroll=page.getByRole('region',{name:'Scrollable comparator availability',exact:true});
  await scroll.focus();await expect(scroll).toBeFocused();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
});

test('legacy comparator archives retain explicit unavailable attempt metadata',async({page,request})=>{
  const legacy=await(await request.get('/api/runs/current')).json();delete legacy.portfolio.comparator_catalog;
  await page.route('**/api/runs/current',route=>route.fulfill({json:legacy}));
  await page.goto('/');await page.getByRole('button',{name:'Validation Lab',exact:true}).click();
  await expect(page.getByText('Comparator availability was not recorded in this archive. Missing attempts are not reconstructed.',{exact:true})).toBeVisible();
  await expect(page.getByRole('table',{name:'Declared comparator availability',exact:true})).toHaveCount(0);
});
