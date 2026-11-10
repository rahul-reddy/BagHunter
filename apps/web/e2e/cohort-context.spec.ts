import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('Museum filters dated benchmark regimes and retains correlated anchors and source clocks',async({page,request})=>{
  const run=await(await request.get('/api/runs/current')).json();
  await page.goto('/');await page.getByRole('button',{name:'100-Bagger Museum',exact:true}).click();
  const panel=page.getByRole('region',{name:'Dated cohort explorer',exact:true});
  await panel.getByLabel('Cohort anchor').selectOption('ALL');
  const labels=run.study.cohorts.labels.filter((row:{horizon_years:number})=>row.horizon_years===1);
  await expect(panel.getByRole('listitem')).toHaveCount(labels.length);
  const regime=labels.find((row:{regime:string})=>row.regime!=='UNAVAILABLE').regime;
  await panel.getByRole('combobox',{name:'Cohort regime (dated benchmark proxy)',exact:true}).selectOption(regime);
  await expect(panel.getByRole('listitem')).toHaveCount(labels.filter((row:{regime:string})=>row.regime===regime).length);
  await panel.getByRole('combobox',{name:'Cohort sector',exact:true}).selectOption('Fixture industrials');
  await expect(panel.getByRole('listitem')).toHaveCount(labels.filter((row:{regime:string;sector:string})=>row.regime===regime && row.sector==='Fixture industrials').length);
  await expect(panel).toContainText('Overlapping horizons and repeated securities are correlated');
  await expect(page.getByText('Matching basis: DATED_INDUSTRY_METADATA.',{exact:false})).toBeVisible();
  const report=await(await request.get(`/api/runs/${run.run_id}/reports/cohort_grid.json`)).json();
  expect(report).toEqual(run.study.cohorts);
  for(const row of report.labels) {
    const cutoff=Date.parse(`${row.anchor}T23:00:00Z`);
    if(row.industry_context.latest_publication) expect(Date.parse(row.industry_context.latest_publication)).toBeLessThanOrEqual(cutoff);
    if(row.benchmark_context.latest_publication) expect(Date.parse(row.benchmark_context.latest_publication)).toBeLessThanOrEqual(cutoff);
  }
  const historical=await(await request.get(`/api/runs/${run.run_id}/reports/historical_cases.md`)).text();
  expect(historical).toContain('DATED_INDUSTRY_METADATA');expect(historical).toContain('fixture-industry-v1');
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  await page.setViewportSize({width:390,height:844});
  const filter=panel.getByRole('combobox',{name:'Cohort regime (dated benchmark proxy)',exact:true});await filter.focus();await expect(filter).toBeFocused();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
});

test('legacy cohort archives expose unavailable regimes instead of recomputing classifications',async({page,request})=>{
  const run=await(await request.get('/api/runs/current')).json();
  for(const row of run.study.cohorts.labels) {delete row.regime;delete row.benchmark_context;delete row.industry_context;delete row.industry_asof;}
  await page.route('**/api/runs/current',route=>route.fulfill({json:run}));
  await page.goto('/');await page.getByRole('button',{name:'100-Bagger Museum',exact:true}).click();
  const panel=page.getByRole('region',{name:'Dated cohort explorer',exact:true});
  const filter=panel.getByRole('combobox',{name:'Cohort regime (dated benchmark proxy)',exact:true});
  await filter.selectOption('UNAVAILABLE');
  await expect(filter.getByRole('option',{name:'UP_63D',exact:true})).toHaveCount(0);
  await expect(panel.getByRole('listitem').first()).toContainText('regime UNAVAILABLE');
});
