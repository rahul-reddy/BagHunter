import {test, expect, type Page} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {emptyAssumptions, emptyNotes, parseAssumptions, restoreResearch} from '../src/observationResearch';

const snapshot = 'e'.repeat(64), checksum = 'f'.repeat(64), first = 'a'.repeat(64), second = 'b'.repeat(64);
const coverage = {mode:'EXTERNAL_UNVERIFIED', snapshot_id:snapshot, source_sha256:checksum, retrieved_at:'2023-06-01T00:00:00Z', ingested_at:'2023-06-01T00:01:00Z', rows:1, missing:{market_cap_reported:0, price_reported:0, change_fraction:0}, zero_pe_reported:0, flags:['UNVERIFIED_SECURITY_IDENTITY'], status:'Fictional browser fixture', provider_observation_time:null};
const sourceContext = {mode:'EXTERNAL_UNVERIFIED', snapshot_id:snapshot, ticker:'FICT'};
function evidence(id = first) {
  const cik = id === first ? '0000000001' : '0000000002';
  const entity = `sec-cik-${cik}-unverified`;
  const citation = {metric:'annual_revenue', value:1000000, unit:'USD', period_end:'2022-12-31', accession:'fixture-filing', accepted_at:'2023-03-01T12:00:00Z', published_at:'2023-03-02T00:00:00Z', source_url:'https://www.sec.gov/Archives/fixture-issuer.htm'};
  const row = {period_end:'2022-12-31', revenue:1000000, revenue_growth:.2, growth_acceleration:null, operating_margin:.1, net_margin:null, cashflow_margin:null, citations:[citation]};
  return {bundle_id:id, manifest:{cik,security_id:entity,asof:'2023-05-01T00:00:00Z',lag_hours:24,submissions:{url:'https://data.sec.gov/submissions/fixture.json',sha256:'1'.repeat(64),retrieved_at:'2023-05-02T00:00:00Z'},companyfacts:{url:'https://data.sec.gov/api/xbrl/companyfacts/fixture.json',sha256:'2'.repeat(64),retrieved_at:'2023-05-02T00:00:00Z'}},issuer:{name:id === first ? 'Fictional issuer one' : 'Fictional issuer two',tickers:['FICTIONAL'],exchanges:['NYSE'],scope:'CURRENT_ISSUER_METADATA_NOT_SECURITY_MAPPING',source_sha256:'1'.repeat(64),retrieved_at:'2023-05-02T00:00:00Z'},financial_profile:{policy:'sec-entity-profile-v1',asof:'2023-05-01T00:00:00Z',security_id:entity,periods:1,status:'DESCRIPTIVE_ENTITY_FINANCIALS_NOT_SECURITY_RANKING',latest:row,series:[row],limitations:['Fictional test source; no empirical evidence']}};
}
async function setup(page: Page) {
  await page.route('**/api/finviz/snapshots', route => route.fulfill({json:{snapshots:[{...coverage}]}}));
  await page.route('**/api/finviz/observations?**', route => route.fulfill({json:{coverage,age_hours:1,stale:false,total:1,offset:0,limit:50,facets:{sectors:['Fixture'],countries:['USA']},observations:[{ticker:'FICT',company:'Fictional current observation',sector:'Fixture',industry:'Fixture industry',country:'USA',market_cap_reported:'777.77',price_reported:'999.99',pe_reported:'15',change_percent_reported:'1',volume_shares:'1000',security_id:null,security_type:'unknown'}]}}));
  await page.route('**/api/sec/bundles', route => route.fulfill({json:{bundles:[first,second].map(id => ({bundle_id:id,cik:evidence(id).manifest.cik,asof:'2023-05-01T00:00:00Z'}))}}));
  await page.goto('/');
  await page.getByRole('button',{name:'Finviz Observations',exact:true}).click();
  await page.getByLabel('Saved Finviz snapshot').selectOption(`EXTERNAL_UNVERIFIED:${snapshot}`);
  await page.getByRole('button',{name:'Research observation FICT',exact:true}).click();
}
async function downloadText(page: Page, name: string) {
  const pending = page.waitForEvent('download');
  await page.getByRole('button',{name,exact:true}).click();
  const download = await pending; const chunks: Buffer[] = [];
  for await (const part of (await download.createReadStream())!) chunks.push(Buffer.from(part));
  return {name:download.suggestedFilename(), text:Buffer.concat(chunks).toString()};
}
async function fillAssumptions(page: Page) {
  for (const [label,value] of Object.entries({'Research starting shares (assumption)':'100000','Research net debt (USD assumption)':'0','Research reference price (USD assumption)':'10','Research annual dilution (fraction)':'0.02','Research annual revenue growth (fraction)':'0.1','Research operating margin (fraction)':'0.15','Research EV / operating earnings multiple':'15'})) await page.getByLabel(label,{exact:true}).fill(value);
}

test('current observation research combines explicit issuer evidence, assumption scenarios and source-bound memos', async ({page}) => {
  test.setTimeout(90_000); let verifications = 0;
  await page.route('**/api/sec/bundles/*?**', route => {verifications++; return route.fulfill({json:evidence(new URL(route.request().url()).pathname.split('/').at(-1)!)});});
  await setup(page);
  await expect(page.getByLabel('Research starting revenue (USD assumption)',{exact:true})).toHaveValue('');
  await expect(page.getByLabel('Research reference price (USD assumption)',{exact:true})).toHaveValue('');
  await page.getByLabel('Observation research hypothesis',{exact:true}).fill('Fictional hypothesis requires independent verification');
  await page.getByLabel('Attach saved SEC issuer evidence',{exact:true}).selectOption(first);
  await expect(page.getByText('Selected SEC filer:',{exact:false})).toContainText('Fictional issuer one');
  await page.getByRole('button',{name:'Use selected SEC annual revenue as an assumption',exact:true}).click();
  await expect(page.getByLabel('Research starting revenue (USD assumption)',{exact:true})).toHaveValue('1000000');
  await expect(page.getByLabel('Research starting shares (assumption)',{exact:true})).toHaveValue('');
  await expect(page.getByLabel('Research reference price (USD assumption)',{exact:true})).toHaveValue('');
  await fillAssumptions(page);
  await page.getByRole('button',{name:'Calculate research scenarios',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Base assumption case',exact:true}).locator('..')).toContainText('$28.22');
  const memo = await downloadText(page,'Export observation research memo');
  expect(memo.name).toBe('UNVERIFIED-FICT-memo.md');
  expect(memo.text).toContain('not a verified security/class mapping');
  expect(memo.text).toContain('https://www.sec.gov/Archives/fixture-issuer.htm');
  expect(memo.text).toContain('Fictional hypothesis requires independent verification');
  expect(memo.text).toContain('### Base');
  const dossier = JSON.parse((await downloadText(page,'Export observation dossier')).text);
  expect(dossier.source.snapshot_id).toBe(snapshot);
  expect(dossier.observation.security_id).toBeNull();
  expect(dossier.issuer_evidence.association_status).toBe('OPERATOR_SELECTED_ENTITY_NOT_VERIFIED_SECURITY_MAPPING');
  expect(dossier.issuer_evidence.bundle_id).toBe(first); expect(dossier.scenarios).toHaveLength(3);
  await page.getByRole('button',{name:'Save observation draft',exact:true}).click();
  await page.getByRole('button',{name:'Close observation desk',exact:true}).click();
  await page.getByRole('button',{name:'Research observation FICT',exact:true}).click();
  await page.getByRole('button',{name:'Load observation draft',exact:true}).click();
  await expect(page.getByRole('button',{name:'Use selected SEC annual revenue as an assumption',exact:true})).toBeVisible();
  expect(verifications).toBeGreaterThan(1);
  await expect(page.getByRole('heading',{name:'Base assumption case',exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'Calculate research scenarios',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Base assumption case',exact:true})).toBeVisible();
  await page.getByLabel('Research operating margin (fraction)',{exact:true}).fill('0.2');
  expect(JSON.parse((await downloadText(page,'Export observation dossier')).text).scenarios).toBeNull();
  await page.getByText('Inspect attached annual financial evidence',{exact:true}).click();
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
});

test('failed or switched issuer verification cannot export stale evidence or scenario results', async ({page}) => {
  test.setTimeout(60_000); let wrong = false;
  await page.route('**/api/sec/bundles/*?**', route => {
    const id = new URL(route.request().url()).pathname.split('/').at(-1)!;
    const body = evidence(id); if (wrong) body.financial_profile.security_id = 'wrong-entity';
    return route.fulfill({json:body});
  });
  await setup(page);
  await page.getByLabel('Attach saved SEC issuer evidence',{exact:true}).selectOption(first);
  await expect(page.getByText('Selected SEC filer:',{exact:false})).toContainText('Fictional issuer one');
  await page.getByRole('button',{name:'Use selected SEC annual revenue as an assumption',exact:true}).click();
  await fillAssumptions(page);
  await page.getByRole('button',{name:'Calculate research scenarios',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Base assumption case',exact:true})).toBeVisible();
  wrong = true;
  await page.getByRole('button',{name:'Reload issuer evidence',exact:true}).click();
  await expect(page.getByRole('region',{name:'Selected SEC issuer evidence',exact:true}).getByRole('alert')).toContainText('does not match');
  await expect(page.getByRole('button',{name:'Export observation dossier',exact:true})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Calculate research scenarios',exact:true})).toBeDisabled();
  await expect(page.getByText('Selected SEC filer:',{exact:false})).toHaveCount(0);
  await expect(page.getByRole('heading',{name:'Base assumption case',exact:true})).toHaveCount(0);
  wrong = false;
  await page.getByLabel('Attach saved SEC issuer evidence',{exact:true}).selectOption(second);
  await expect(page.getByText('Selected SEC filer:',{exact:false})).toContainText('Fictional issuer two');
  expect(JSON.parse((await downloadText(page,'Export observation dossier')).text).issuer_evidence.bundle_id).toBe(second);
  await page.getByLabel('Attach saved SEC issuer evidence',{exact:true}).selectOption('');
  const exported = JSON.parse((await downloadText(page,'Export observation dossier')).text);
  expect(exported.issuer_evidence).toBeNull(); expect(exported.scenarios).toBeNull();
  await page.getByLabel('Research starting revenue (USD assumption)',{exact:true}).fill('1'.repeat(101));
  await page.getByRole('button',{name:'Save observation draft',exact:true}).click();
  await expect(page.getByText('Draft contains an invalid date or assumption value. Correct it before saving.',{exact:true})).toBeVisible();
  expect(await page.evaluate(key => localStorage.getItem(key),`baghunter.observation.v1.EXTERNAL_UNVERIFIED.${snapshot}.FICT`)).toBeNull();
});

test('an older issuer response cannot replace a newly selected archive', async ({page}) => {
  let release: (() => void) | undefined;
  const gate = new Promise<void>(resolve => {release = resolve;});
  let requested = false;
  await page.route('**/api/sec/bundles/*?**', async route => {
    const id = new URL(route.request().url()).pathname.split('/').at(-1)!;
    if (id === first) {requested = true; await gate;}
    await route.fulfill({json:evidence(id)}).catch(() => {}); // The old request may have been aborted.
  });
  await setup(page);
  await page.getByLabel('Attach saved SEC issuer evidence',{exact:true}).selectOption(first);
  await expect.poll(() => requested).toBe(true);
  await page.getByLabel('Attach saved SEC issuer evidence',{exact:true}).selectOption(second);
  await expect(page.getByText('Selected SEC filer:',{exact:false})).toContainText('Fictional issuer two');
  release!();
  const exported = JSON.parse((await downloadText(page,'Export observation dossier')).text);
  expect(exported.issuer_evidence.bundle_id).toBe(second);
  expect(exported.issuer_evidence.issuer.name).toBe('Fictional issuer two');
});

test('saved-draft and numeric parsing preserve missingness and reject source/context corruption', () => {
  const legacy = {source_sha256:checksum,draft:{...emptyNotes,hypothesis:'Legacy user assertion'}};
  const restored = restoreResearch(legacy,checksum,sourceContext);
  expect(restored.inputs.revenue).toBe(''); expect(restored.bundleId).toBe('');
  expect(parseAssumptions(restored.inputs)).toBeNull();
  const valid = {schema:'observation-research-v2',source_sha256:checksum,source_context:sourceContext,draft:{...emptyNotes},sec_bundle_id:first,scenario_assumptions:{...emptyAssumptions}};
  expect(restoreResearch(valid,checksum,sourceContext).bundleId).toBe(first);
  for (const changed of [{...valid,source_sha256:'wrong'},{...valid,source_context:{...sourceContext,ticker:'OTHER'}},{...valid,sec_bundle_id:'../.env'},{...valid,draft:{...emptyNotes,review_date:'2023-02-30'}},{...valid,scenario_assumptions:{...emptyAssumptions,revenue:'Infinity'}}]) expect(() => restoreResearch(changed,checksum,sourceContext)).toThrow();
  expect(parseAssumptions({...emptyAssumptions,net_debt:'0'})).toBeNull();
});
