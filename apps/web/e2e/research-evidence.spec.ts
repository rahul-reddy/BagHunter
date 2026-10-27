import {test, expect, type Page} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {compareTime, awareTime, criticStatus, distinctReviewer, emptyWorkspace, evidenceStatus, parseCritic, peerBands, requestDigest, validateWorkspace, type PeerItem, type QualitativeItem} from '../src/researchEvidence';
import {emptyAssumptions, emptyNotes, restoreResearch} from '../src/observationResearch';

const asof = '2023-06-01T00:00:00Z', snapshot = 'a'.repeat(64), checksum = 'b'.repeat(64);
const context = {mode: 'EXTERNAL_UNVERIFIED', snapshot_id: snapshot, ticker: 'FICT'};
const qualitative = (): QualitativeItem => ({id:'q1', category:'Competitive moat', statement:'Fictional primary-source transcription', kind:'PRIMARY_SOURCE_TRANSCRIPTION', attribution:'Primary researcher', source_url:'https://www.sec.gov/Archives/fixture.htm', published_at:'2023-03-01T12:00:00Z', disconfirmation:'Loss of the fictional contract'});
const peer = (id: string, multiple: string, extra: Partial<PeerItem> = {}): PeerItem => ({id, company:id, metric:'P_E', basis:'TTM 2023-03-31', currency:'USD', multiple, source_url:'https://www.sec.gov/Archives/fixture.htm', published_at:'2023-03-01T12:00:00Z', rationale:'Fictional comparable business', ...extra});

test('typed research rejects corrupt records, clocks, URLs and unsupported values', () => {
  expect(awareTime('2023-02-30T12:00:00Z')).toBe(false);
  expect(awareTime('2023-03-01T12:00:00')).toBe(false);
  expect(awareTime('2023-03-01T24:00:00Z')).toBe(false);
  expect(compareTime('2023-03-01T12:00:00.000000001Z','2023-03-01T12:00:00Z')).toBe(1);
  expect(compareTime('2023-03-01T07:00:00.123456789-05:00','2023-03-01T12:00:00.123456789Z')).toBe(0);
  expect(awareTime('2023-03-01T12:00:00.1234567890Z')).toBe(false);
  const valid = {...emptyWorkspace(asof), qualitative:[qualitative()], peers:[peer('p1','10')]};
  expect(validateWorkspace(valid)).toEqual(valid);
  expect(() => validateWorkspace(valid, '2023-07-01T00:00:00Z')).toThrow();
  for (const changed of [{...valid, research_asof:'2023-02-30T12:00:00Z'}, {...valid, time_to_thesis_months:'0'}, {...valid, qualitative:[qualitative(), qualitative()]}, {...valid, peers:[peer('p1','Infinity')]}, {...valid, peers:[peer('p1','-1')]}, {...valid, qualitative:[{...qualitative(), source_url:'https://user:password@example.invalid/'}]}, {...valid, peers:Array.from({length:51}, (_,i) => peer(String(i),'10'))}, {...valid, critic:{}}]) expect(() => validateWorkspace(changed)).toThrow();
  const saved = {schema:'observation-research-v3', source_sha256:checksum, source_context:context, draft:{...emptyNotes}, scenario_assumptions:{...emptyAssumptions}, sec_bundle_id:'', research_workspace:valid};
  expect(restoreResearch(saved, checksum, context).workspace).toEqual(valid);
  expect(() => restoreResearch({...saved, source_context:{...context,ticker:'OTHER'}}, checksum, context)).toThrow();
  expect(restoreResearch({source_sha256:checksum,draft:{...emptyNotes}}, checksum, context).workspace).toBeNull();
});

test('peer bands retain incompatible, future, missing, zero and duplicate exclusions', () => {
  const workspace = {...emptyWorkspace(asof), peers:[peer('a','10'), peer('b','20'), peer('c','3',{metric:'EV_REVENUE'}), peer('d','100',{published_at:'2023-07-01T00:00:00Z'}), peer('e','0'), peer('f','4',{currency:'EUR'}), peer('g','5',{basis:'NTM'}), peer('h','6',{source_url:''})]};
  const report = peerBands(workspace);
  expect(report.groups).toHaveLength(4);
  expect(report.groups.find(group => group.count === 2)?.median).toBe(15);
  expect(report.excluded.map(row => row.reason)).toEqual(['FUTURE_AT_RESEARCH_CLOCK','NONPOSITIVE_MULTIPLE','INCOMPLETE_COMPARISON_OR_DATED_SOURCE']);
  const duplicates = peerBands({...workspace, peers:[peer('a','10',{company:'Same firm'}),peer('b','20',{company:' same   FIRM '})]});
  expect(duplicates.groups).toEqual([]);
  expect(duplicates.excluded.every(row => row.reason === 'DUPLICATE_PEER_COMPANY_IN_COMPARISON')).toBe(true);
  expect(peerBands({...workspace, peers:[peer('bad','NaN')]}).groups).toEqual([]);
  expect(evidenceStatus({...qualitative(), kind:'LLM_JUDGMENT'}, asof)).toBe('ATTRIBUTED_JUDGMENT_NOT_VERIFIED_FACT');
  expect(evidenceStatus({...qualitative(), published_at:'2023-07-01T00:00:00Z'}, asof)).toBe('FUTURE_AT_RESEARCH_CLOCK');
});

test('critic fingerprints are canonical, source-bound and never certify independence', async () => {
  const digest = await requestDigest({source:{id:'one', hash:'a'}, input:{b:2,a:1}});
  expect(digest).toBe(await requestDigest({input:{a:1,b:2},source:{hash:'a',id:'one'}}));
  expect(digest).not.toBe(await requestDigest({source:{id:'one',hash:'changed'},input:{b:2,a:1}}));
  await expect(requestDigest({value:NaN})).rejects.toThrow();
  await expect(requestDigest({value:undefined})).rejects.toThrow();
  const review = parseCritic({schema:'research-critic-v1',request_digest:digest,reviewer:'Separate critic',reviewer_kind:'HUMAN',counterargument:'Fictional counterargument',evidence_gaps:'Unknown customer concentration',falsification:'Contract cancelled',citations:[{url:'https://www.sec.gov/Archives/fixture.htm',published_at:'2023-03-01T12:00:00Z'}]});
  const workspace = {...emptyWorkspace(asof),author:'Primary researcher',critic:review};
  expect(criticStatus(workspace,digest)).toBe('MATCHES_REQUEST_INDEPENDENCE_NOT_VERIFIED');
  expect(criticStatus(workspace,'0'.repeat(64))).toBe('STALE_REQUEST');
  expect(distinctReviewer(' Primary researcher ','primary RESEARCHER')).toBe(false);
  expect(criticStatus({...workspace,critic:{...review,reviewer:'PRIMARY RESEARCHER'}},digest)).toBe('DISTINCT_ATTRIBUTION_REQUIRED');
  expect(criticStatus({...workspace,critic:{...review,citations:[]}},digest)).toBe('CRITIC_SOURCES_MISSING');
});

async function setup(page: Page) {
  const coverage = {mode:context.mode,snapshot_id:snapshot,source_sha256:checksum,retrieved_at:asof,ingested_at:asof,rows:1,missing:{},zero_pe_reported:0,flags:['UNVERIFIED_SECURITY_IDENTITY'],status:'Fictional browser fixture',provider_observation_time:null};
  await page.route('**/api/runs/current', route => route.fulfill({status:503,json:{}}));
  await page.route('**/api/finviz/snapshots', route => route.fulfill({json:{snapshots:[coverage]}}));
  await page.route('**/api/finviz/observations?**', route => route.fulfill({json:{coverage,age_hours:1,stale:false,total:1,offset:0,limit:50,facets:{sectors:['Fixture'],countries:['USA']},observations:[{ticker:'FICT',company:'Fictional company',sector:'Fixture',industry:'Fixture',country:'USA',market_cap_reported:null,price_reported:null,pe_reported:null,change_percent_reported:null,volume_shares:'1000',security_id:null,security_type:'unknown'}]}}));
  await page.route('**/api/sec/bundles', route => route.fulfill({json:{bundles:[]}}));
  await page.goto('/');
  await page.getByRole('button',{name:'Finviz Observations',exact:true}).click();
  await page.getByLabel('Saved Finviz snapshot').selectOption(`${context.mode}:${snapshot}`);
  await page.getByRole('button',{name:'Research observation FICT',exact:true}).click();
}
async function exported(page: Page, name: string) {
  const pending = page.waitForEvent('download'); await page.getByRole('button',{name,exact:true}).click();
  const parts: Buffer[] = []; for await (const part of (await (await pending).createReadStream())!) parts.push(Buffer.from(part));
  return Buffer.concat(parts).toString();
}

test('source-bound structured research, peer bands and separate critique persist and become stale after edits', async ({page}) => {
  test.setTimeout(90_000); await setup(page);
  await page.getByLabel('Primary research author',{exact:true}).fill('Primary researcher');
  await page.getByLabel('Time to thesis (months assumption)',{exact:true}).fill('0');
  await expect(page.getByRole('button',{name:'Export observation dossier',exact:true})).toBeDisabled();
  await page.getByLabel('Time to thesis (months assumption)',{exact:true}).fill('24');
  await page.getByLabel('Time-to-thesis milestones and conditions',{exact:true}).fill('Fictional product must reach a cited milestone.');
  await page.getByLabel('Opportunity cost and alternative use of capital',{exact:true}).fill('Compare this assumption with holding cash; returns remain unknown.');
  await page.getByText('Qualitative primary-source evidence',{exact:true}).click();
  for (const [label,value] of Object.entries({'Qualitative statement':'Fictional contract needs independent verification','Evidence author or model attribution':'Primary researcher','Qualitative primary source URL':'https://www.sec.gov/Archives/fixture.htm','Qualitative publication timestamp (ISO with timezone)':'2023-03-01T12:00:00Z','Qualitative disconfirmation condition':'Contract is cancelled'})) await page.getByLabel(label,{exact:true}).fill(value);
  await page.getByRole('combobox',{name:'Evidence judgment type',exact:true}).selectOption('HUMAN_JUDGMENT');
  await page.getByRole('button',{name:'Add qualitative evidence',exact:true}).click();
  await expect(page.getByText('Human judgment · Attributed judgment; not a verified fact',{exact:false})).toBeVisible();
  await page.getByText('Cited peer valuation comparisons',{exact:true}).click();
  for (const [name,multiple] of [['Peer one','10'],['Peer two','20']]) {
    for (const [label,value] of Object.entries({'Peer company':name,'Peer denominator period basis':'TTM 2023-03-31','Peer reporting currency':'USD','Reported peer multiple':multiple,'Peer primary source URL':'https://www.sec.gov/Archives/fixture.htm','Peer publication timestamp (ISO with timezone)':'2023-03-01T12:00:00Z','Peer comparability rationale':'Fictional comparable business'})) await page.getByLabel(label,{exact:true}).fill(value);
    await page.getByRole('button',{name:'Add peer comparison',exact:true}).click();
  }
  await expect(page.getByRole('table',{name:'User-transcribed peer valuation bands',exact:true})).toContainText('15×');
  await page.getByText('Separately attributed adversarial critique',{exact:true}).click();
  const packet = JSON.parse(await exported(page,'Export separate critic request'));
  expect(packet.request_digest).toBe(await requestDigest(packet.context));
  expect(packet.context.source.source_sha256).toBe(checksum);
  const review = {schema:'research-critic-v1',request_digest:packet.request_digest,reviewer:'Separate critic',reviewer_kind:'HUMAN',counterargument:'Fictional alternative explanation; the thesis is unsupported.',evidence_gaps:'Independent contract verification missing.',falsification:'Contract cancelled.',citations:[{url:'https://www.sec.gov/Archives/fixture.htm',published_at:'2023-03-01T12:00:00Z'}]};
  await page.getByLabel('Separate critic response JSON',{exact:true}).fill(JSON.stringify({...review,reviewer:'Primary researcher'}));
  await page.getByRole('button',{name:'Attach separately attributed critic',exact:true}).click();
  await expect(page.getByText('Enter a research author and a distinct reviewer attribution.',{exact:true})).toBeVisible();
  await page.getByLabel('Separate critic response JSON',{exact:true}).fill(JSON.stringify(review));
  await page.getByRole('button',{name:'Attach separately attributed critic',exact:true}).click();
  await expect(page.getByText('Review matches this packet; independence remains unverified',{exact:true})).toBeVisible();
  await page.getByLabel('Time to thesis (months assumption)',{exact:true}).fill('36');
  await expect(page.getByText('Critic review is stale; the research packet changed',{exact:true})).toBeVisible();
  const dossier = JSON.parse(await exported(page,'Export observation dossier'));
  expect(dossier.schema).toBe('observation-research-v3'); expect(dossier.critic_status).toBe('STALE_REQUEST');
  expect(dossier.peer_comparisons.groups[0].median).toBe(15);
  expect(dossier.research_workspace.qualitative[0].kind).toBe('HUMAN_JUDGMENT');
  expect((await exported(page,'Export observation research memo'))).toContain('Horizon assumption: 36 months');
  await page.getByRole('button',{name:'Save observation draft',exact:true}).click();
  await page.getByRole('button',{name:'Close observation desk',exact:true}).click();
  await page.getByRole('button',{name:'Research observation FICT',exact:true}).click();
  await page.getByRole('button',{name:'Load observation draft',exact:true}).click();
  await expect(page.getByLabel('Time to thesis (months assumption)',{exact:true})).toHaveValue('36');
  await page.getByText('Separately attributed adversarial critique',{exact:true}).click();
  await expect(page.getByText('Critic review is stale; the research packet changed',{exact:true})).toBeVisible();
  await page.getByText('Qualitative primary-source evidence',{exact:true}).click();
  await page.getByText('Cited peer valuation comparisons',{exact:true}).click();
  await expect(page.getByRole('link',{name:'Open qualitative source',exact:true})).toHaveAttribute('href','https://www.sec.gov/Archives/fixture.htm');
  await expect(page.getByRole('link',{name:'Open peer source',exact:true}).first()).toBeVisible();
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
});
