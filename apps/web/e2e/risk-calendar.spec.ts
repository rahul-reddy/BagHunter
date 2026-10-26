import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('daily marks, risk metrics and execution filters have explicit sampling', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button', {name: 'Validation Lab', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Daily marked portfolio risk'})).toBeVisible();
  await expect(page.getByText('Daily-close maximum drawdown', {exact: true})).toBeVisible();
  await expect(page.getByRole('img', {name: 'Daily marked fixture portfolio equity per initial dollar including cash gaps'})).toBeVisible();
  await page.getByLabel('Execution security').selectOption('fx-compound');
  await expect(page.getByRole('table', {name: 'Constrained simulation execution ledger'})).not.toContainText('fx-steady');
  await page.getByLabel('Execution year').selectOption('2020');
  const ledger = page.getByRole('table', {name: 'Constrained simulation execution ledger'});
  await expect(ledger).toContainText('2020-');
  await expect(ledger).not.toContainText('2019-');
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('dated catalysts persist, filter and export without becoming verified evidence', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button', {name: 'Thesis Studio', exact: true}).click();
  await page.getByLabel('Catalyst date', {exact: true}).fill('2026-11-01');
  await page.getByLabel('Catalyst title').fill('Fictional product review');
  await page.getByLabel('Catalyst source URL').fill('javascript:alert(1)');
  await page.getByRole('button', {name: 'Add catalyst event'}).click();
  await expect(page.getByRole('alert')).toContainText('HTTPS source');
  await page.getByLabel('Catalyst source URL').fill('https://issuer.example.org/fictional');
  await page.getByLabel('Event falsification condition').fill('Publication does not confirm launch');
  await page.getByRole('button', {name: 'Add catalyst event'}).click();
  await expect(page.getByRole('table', {name: 'Dated catalyst assertions for DEMO-A'})).toContainText('Fictional product review');
  await page.getByLabel('Status for Fictional product review').selectOption('OBSERVED');
  await page.reload();
  await page.getByRole('button', {name: 'Thesis Studio', exact: true}).click();
  await expect(page.getByLabel('Status for Fictional product review')).toHaveValue('OBSERVED');
  await page.getByLabel('Calendar status filter').selectOption('PLANNED');
  await expect(page.getByRole('button', {name: 'Remove Fictional product review'})).toHaveCount(0);
  await page.getByLabel('Calendar status filter').selectOption('ALL');
  const pending = page.waitForEvent('download');
  await page.getByRole('button', {name: 'Export catalyst calendar'}).click();
  expect((await pending).suggestedFilename()).toBe('FIXTURE-fx-compound-catalysts.json');
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  await page.getByRole('button', {name: 'Remove Fictional product review'}).click();
  await expect(page.getByText('No catalyst events saved.', {exact: false})).toBeVisible();
});
