import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir } from 'node:fs/promises';

test('pipeline to browser: candidate factors, source evidence, hindsight and evaluation', async ({page}) => {
  await page.goto('/');
  await expect(page).toHaveTitle('BagHunter · Research Lab');
  await expect(page.getByRole('heading', {name: 'Command Center'})).toBeVisible();
  await expect(page.getByRole('button', {name: 'DEMO-A fx-compound'})).toBeVisible();
  await expect(page.getByText('STALE / FIXTURE', {exact: false})).toBeVisible();
  await page.getByRole('button', {name: /Score breakdown for DEMO-A/}).click();
  await expect(page.getByRole('heading', {name: 'Score ingredients'})).toBeVisible();
  await expect(page.getByText('Missing', {exact: false}).first()).toBeVisible();
  await expect(page.getByRole('link', {name: 'FIXTURE-0-2021 ↗'})).toBeVisible();
  const source = await page.request.get('/api/sources/fixture-v1');
  expect((await source.json()).mode).toBe('FIXTURE');
  await page.getByRole('button', {name: '100-Bagger Museum', exact: true}).click();
  await expect(page.getByText('fx-compound vs fx-failure')).toBeVisible();
  await expect(page.getByText('INCOMPLETE HORIZON').first()).toBeVisible();
  await page.getByRole('button', {name: 'Validation Lab', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Walk-forward mechanics'})).toBeVisible();
  await expect(page.getByText('Next weekday open', {exact: false})).toBeVisible();
  await page.getByRole('button', {name: 'Data Quality', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Source ledger'})).toBeVisible();
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  await page.getByRole('button', {name: 'BagHunter Radar', exact: true}).click();
  await page.getByLabel('Find a security').fill('no-such-security');
  await expect(page.getByText('No securities match these filters.')).toBeVisible();
  await page.getByLabel('Find a security').fill('fx-compound');
  await expect(page.getByRole('button', {name: 'DEMO-A fx-compound'})).toBeVisible();
});

test('desktop and mobile accessibility, layout and screenshots', async ({page}) => {
  await mkdir('../../artifacts/screenshots', {recursive: true});
  await page.goto('/');
  await expect(page.getByRole('button', {name: 'DEMO-A fx-compound'})).toBeVisible();
  const desktop = await new AxeBuilder({page}).analyze();
  expect(desktop.violations).toEqual([]);
  await page.screenshot({path: '../../artifacts/screenshots/command-center.png', fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  const mobile = await new AxeBuilder({page}).analyze();
  expect(mobile.violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({path: '../../artifacts/screenshots/mobile.png', fullPage: true});
});

test('unavailable backend displays an actionable error instead of fake results', async ({page}) => {
  await page.route('**/api/runs/current', route => route.fulfill({status: 503, body: '{}'}));
  await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('uv run baghunter demo');
  await expect(page.getByRole('button', {name: 'DEMO-A fx-compound'})).toHaveCount(0);
});
