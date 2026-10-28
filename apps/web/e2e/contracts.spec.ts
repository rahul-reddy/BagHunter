import {execFileSync} from 'node:child_process';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {createHash} from 'node:crypto';

test('saved canonical tables expose hashes, null provenance and verified Parquet downloads', async ({page}) => {
  await page.goto('/');await page.getByRole('button',{name:'Data Quality',exact:true}).click();
  const panel = page.getByRole('region',{name:'Saved canonical data contracts',exact:true});
  const table = panel.getByRole('table',{name:'Saved canonical table inventory',exact:true});
  await expect(table.getByRole('row')).toHaveCount(11);
  await expect(table.getByRole('row').filter({has:page.getByRole('rowheader',{name:'instrument',exact:true})})).toContainText('cik: 4');
  await expect(table.getByRole('row').filter({has:page.getByRole('rowheader',{name:'thesis',exact:true})})).toContainText('Empty table; no observations invented');
  await expect(panel).toContainText('unrecorded intraday times and exit prices stay null');
  const run = await (await page.request.get('/api/runs/current')).json();
  const pending = page.waitForEvent('download');
  await panel.getByRole('link',{name:'Download daily_bar Parquet',exact:true}).click();
  const chunks:Buffer[]=[];for await(const part of (await(await pending).createReadStream())!) chunks.push(Buffer.from(part));
  const body = Buffer.concat(chunks);
  expect(body.subarray(0,4).toString()).toBe('PAR1');
  expect(createHash('sha256').update(body).digest('hex')).toBe(run.data_contracts.tables.daily_bar.sha256);
  await table.getByRole('row').filter({has:page.getByRole('rowheader',{name:'instrument',exact:true})}).getByText('Fields and artifact checksum',{exact:true}).click();
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  await page.setViewportSize({width:390,height:844});
  const scroll = panel.getByRole('region',{name:'Scrollable canonical table inventory',exact:true});
  await scroll.focus();await expect(scroll).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
});

test('legacy run does not manufacture a canonical inventory', async ({page,request}) => {
  const run=await(await request.get('/api/runs/current')).json();delete run.data_contracts;
  await page.route('**/api/runs/current',route=>route.fulfill({json:run}));
  await page.goto('/');await page.getByRole('button',{name:'Data Quality',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Canonical table exports unavailable',exact:true})).toBeVisible();
  await expect(page.getByRole('link',{name:'Download daily_bar Parquet',exact:true})).toHaveCount(0);
});


test('Thesis Studio dossier persists through the offline CLI without verifying its critique', async ({page}) => {
  await page.goto('/');await page.getByRole('button',{name:'Thesis Studio',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Base scenario',exact:true})).toBeVisible();
  const pending=page.waitForEvent('download');
  await page.getByRole('button',{name:'Download thesis dossier',exact:true}).click();
  const root=resolve('../..'),destination=resolve(root,'artifacts/contracts-thesis-dossier.json');
  await mkdir(resolve(root,'artifacts'),{recursive:true});
  await(await pending).saveAs(destination);
  const receipt=JSON.parse(execFileSync('uv',['run','baghunter','import-thesis','--dossier',destination],{cwd:root,encoding:'utf8',timeout:15000}));
  expect(receipt.verified_real_theses).toBe(0);expect(receipt.predictor_promotions).toBe(0);
  expect(receipt.critic_independence_verified).toBe(false);
  expect(receipt.assertion_status).toBe('FIXTURE_UNVERIFIED_OPERATOR_ASSERTIONS_NOT_PREDICTORS');
  expect(receipt.archive_id).toMatch(/^[a-f0-9]{64}$/);
});
