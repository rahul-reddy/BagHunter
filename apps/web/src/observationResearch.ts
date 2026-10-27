import {validateWorkspace, researchEvidenceMemo, type ResearchWorkspace} from './researchEvidence';
import type {Observation} from './FinvizBrowser';
import type {CompanyEvidence} from './CompanyEvidence';

export type ObservationSource = {mode: string; snapshot_id: string; source_sha256: string; retrieved_at: string};
export const emptyNotes = {hypothesis: '', evidence: '', falsification: '', bear: '', review_date: ''};
export type ObservationNotes = typeof emptyNotes;
export const emptyAssumptions = {revenue: '', shares: '', net_debt: '', reference_price: '', years: '3', dilution: '', growth: '', margin: '', multiple: ''};
export type AssumptionStrings = typeof emptyAssumptions;
export type ScenarioInputs = Record<keyof AssumptionStrings, number>;
export type CompanyScenario = {name: string; assumptions: ScenarioInputs; value: {per_share_value: number; annualized_change: number; diluted_shares: number; enterprise_value: number; equity_value: number; status: string}};

export function parseAssumptions(values: AssumptionStrings): ScenarioInputs | null {
  if (Object.values(values).some(value => !value.trim() || !/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(value.trim()) || !Number.isFinite(Number(value)))) return null;
  const result = Object.fromEntries(Object.entries(values).map(([key, value]) => [key, Number(value)])) as ScenarioInputs;
  return Number.isInteger(result.years) ? result : null;
}

export function restoreResearch(value: unknown, checksum: string, context: {mode: string; snapshot_id: string; ticker: string}) {
  const saved = value as {schema?: string; source_sha256?: string; source_context?: typeof context; draft?: ObservationNotes; sec_bundle_id?: string; scenario_assumptions?: AssumptionStrings; research_workspace?: unknown} | null;
  if (!saved || saved.source_sha256 !== checksum || !saved.draft || (saved.schema && !['observation-research-v2', 'observation-research-v3'].includes(saved.schema)) || Object.keys(saved.draft).length !== Object.keys(emptyNotes).length || Object.keys(emptyNotes).some(key => typeof saved.draft![key as keyof ObservationNotes] !== 'string' || saved.draft![key as keyof ObservationNotes].length > 5000)) throw new Error('Invalid observation draft');
  const date = saved.draft.review_date;
  if (['observation-research-v2', 'observation-research-v3'].includes(saved.schema ?? '') && (!saved.source_context || Object.entries(context).some(([key, expected]) => saved.source_context![key as keyof typeof context] !== expected))) throw new Error('Saved observation context mismatch');
  if (date && (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isFinite(Date.parse(date)) || new Date(date).toISOString().slice(0,10) !== date)) throw new Error('Invalid review date');
  const bundleId = saved.sec_bundle_id ?? '';
  if (typeof bundleId !== 'string' || (bundleId && !/^[a-f0-9]{64}$/.test(bundleId))) throw new Error('Invalid saved issuer archive');
  const inputs = saved.scenario_assumptions ?? {...emptyAssumptions};
  if (!inputs || Object.keys(inputs).length !== Object.keys(emptyAssumptions).length || Object.keys(emptyAssumptions).some(key => typeof inputs[key as keyof AssumptionStrings] !== 'string' || inputs[key as keyof AssumptionStrings].length > 100 || (inputs[key as keyof AssumptionStrings] !== '' && !Number.isFinite(Number(inputs[key as keyof AssumptionStrings]))))) throw new Error('Invalid saved assumptions');
  const workspace = saved.schema === 'observation-research-v3' ? validateWorkspace(saved.research_workspace) : null;
  return {draft: saved.draft, bundleId, inputs, workspace};
}

export function observationMemo(source: ObservationSource, observation: Observation, draft: ObservationNotes, evidence: CompanyEvidence | null, scenarios: CompanyScenario[] | null, workspace: ResearchWorkspace | null = null, reviewDigest: string | null = null): string {
  const rows = [`# ${source.mode === 'FIXTURE' ? 'FIXTURE' : 'UNVERIFIED'} observation research — ${observation.ticker}`, '',
    '**User research draft; not a verified investment thesis or forecast.**', '',
    `Reported company: ${observation.company}. Sector: ${observation.sector ?? 'Unavailable'}. Industry: ${observation.industry ?? 'Unavailable'}.`,
    `Finviz snapshot: ${source.snapshot_id}; original CSV SHA-256 ${source.source_sha256}; retrieved ${source.retrieved_at}. Provider observation time is unknown.`,
    `Reported price: ${observation.price_reported ?? 'Missing'}; market cap: ${observation.market_cap_reported ?? 'Missing'}; P/E: ${observation.pe_reported ?? 'Missing'}; volume: ${observation.volume_shares ?? 'Missing'}. Original provider scale/currency/type/identity remain unverified.`,
    '', '## User assertions and research questions', '', `Hypothesis: ${draft.hypothesis || 'Not entered'}`, `Evidence/questions: ${draft.evidence || 'Not entered'}`, `Falsification: ${draft.falsification || 'Not entered'}`, `Bear argument: ${draft.bear || 'Not entered'}`, `Review date: ${draft.review_date || 'Not scheduled'}`, '', '## Explicitly selected SEC entity evidence', ''];
  if (evidence) {
    rows.push(`Operator-selected filer: ${evidence.issuer?.name ?? 'Name unavailable'}; CIK ${evidence.manifest.cik}; bundle ${evidence.bundle_id}.`, '**This attachment is a user association, not a verified security/class mapping.**',
      `Financial clock ${evidence.manifest.asof}; processing lag ${evidence.manifest.lag_hours} hours. Issuer metadata is current at retrieval, not historical identity evidence.`,
      `Submissions: ${evidence.manifest.submissions.url}; SHA-256 ${evidence.manifest.submissions.sha256}; retrieved ${evidence.manifest.submissions.retrieved_at}.`,
      `Companyfacts: ${evidence.manifest.companyfacts.url}; SHA-256 ${evidence.manifest.companyfacts.sha256}; retrieved ${evidence.manifest.companyfacts.retrieved_at}.`);
    const latest = evidence.financial_profile.latest;
    if (latest) {
      rows.push(`Latest selected annual revenue period ${latest.period_end}: ${latest.revenue ?? 'Unavailable'} USD; revenue growth ${latest.revenue_growth ?? 'Unavailable'}; operating margin ${latest.operating_margin ?? 'Unavailable'} (ratios are fractions).`, '', 'Dated filing citations:');
      for (const cite of latest.citations) rows.push(`- ${cite.metric}, period ${cite.period_end}: ${cite.value} ${cite.unit}; accession ${cite.accession}; accepted ${cite.accepted_at}; publication upper bound ${cite.published_at}; ${cite.source_url}`);
    }
    rows.push(...evidence.financial_profile.limitations.map(text => `- ${text}`));
  } else rows.push('No SEC entity evidence attached.');
  rows.push('', '## Assumption scenarios', '', 'These inputs are user assumptions. They do not establish the observation’s identity, currency, class share count or expected return. No probabilities are assigned. Net debt is held constant; no discount-rate, financing, tax or dividend model.');
  if (scenarios?.length) for (const scenario of scenarios) rows.push('', `### ${scenario.name}`, `Assumptions: ${JSON.stringify(scenario.assumptions)}`, `Modeled enterprise value ${scenario.value.enterprise_value}; equity value ${scenario.value.equity_value}; diluted shares ${scenario.value.diluted_shares}; per-share value ${scenario.value.per_share_value}; annualized change ${scenario.value.annualized_change}.`, scenario.value.status);
  else rows.push('No current calculation. Saved inputs require recalculation after loading or changing source/assumptions.');
  if (workspace) rows.push(...researchEvidenceMemo(workspace, reviewDigest));
  rows.push('', '## Limits', '', '- No permanent identity assignment, eligibility approval, screening score or historical activation.', '- SEC aggregate extraction vintages are not certified; a current Finviz snapshot is not a historical investable universe.', '- Source clocks remain separate; this memo does not merge them into a certified point-in-time profile.', '- Independent factual critique, class/share verification, current prices/units and historical coverage remain unresolved.', '- Zero verified investment-thesis status is changed by saving or exporting this draft.');
  return rows.join('\n') + '\n';
}
