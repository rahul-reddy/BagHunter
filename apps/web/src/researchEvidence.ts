/** Source-bound operator research. These records never enter scoring or verified facts. */
export const categories = ['Industry catalyst', 'Customer concentration', 'Product release', 'Contract quality', 'Management incentives', 'Competitive moat', 'Narrative saturation', 'Capital raises', 'Market size assumptions', 'Sector cycle'] as const;
export type Judgment = 'PRIMARY_SOURCE_TRANSCRIPTION' | 'HUMAN_JUDGMENT' | 'LLM_JUDGMENT' | 'ASSUMPTION';
export type QualitativeItem = {id: string; category: typeof categories[number]; statement: string; kind: Judgment; attribution: string; source_url: string; published_at: string; disconfirmation: string};
export type PeerItem = {id: string; company: string; metric: 'P_E' | 'EV_REVENUE' | 'EV_OPERATING_INCOME'; basis: string; currency: string; multiple: string; source_url: string; published_at: string; rationale: string};
export type CriticReview = {schema: 'research-critic-v1'; request_digest: string; reviewer: string; reviewer_kind: 'HUMAN' | 'LLM'; counterargument: string; evidence_gaps: string; falsification: string; citations: {url: string; published_at: string}[]};
export type ResearchWorkspace = {author: string; research_asof: string; qualitative: QualitativeItem[]; peers: PeerItem[]; time_to_thesis_months: string; time_to_thesis_conditions: string; opportunity_cost: string; critic: CriticReview | null};
export const emptyWorkspace = (asof: string): ResearchWorkspace => ({author: '', research_asof: asof, qualitative: [], peers: [], time_to_thesis_months: '', time_to_thesis_conditions: '', opportunity_cost: '', critic: null});
const text = (value: unknown, max = 5000): value is string => typeof value === 'string' && value.length <= max;
export const awareTime = (value: string) => /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number(value.slice(11,13)) < 24 && Number(value.slice(14,16)) < 60 && Number(value.slice(17,19)) < 60 && Number.isFinite(Date.parse(value)) && new Date(`${value.slice(0,10)}T00:00:00Z`).toISOString().slice(0,10) === value.slice(0,10);
export function compareTime(left: string, right: string): number {
  const nanos = (value: string) => {
    if (!awareTime(value)) throw new Error('Aware timestamp with at most nine fractional digits required.');
    const fraction = value.match(/\.(\d+)(?:Z|[+-])/ )?.[1] ?? '';
    return BigInt(Math.floor(Date.parse(value)/1000)) * 1_000_000_000n + BigInt(fraction.padEnd(9, '0'));
  };
  const a = nanos(left), b = nanos(right); return a < b ? -1 : a > b ? 1 : 0;
}
export const sourceUrl = (value: string) => {try {const url = new URL(value); return url.protocol === 'https:' && !url.username && !url.password;} catch {return false;}};
const citation = (url: unknown, time: unknown) => text(url, 2048) && (!url || sourceUrl(url)) && text(time, 100) && (!time || awareTime(time));
const keys = (value: object, expected: string[]) => Object.keys(value).length === expected.length && expected.every(key => Object.hasOwn(value, key));

export function parseCritic(value: unknown): CriticReview {
  const review = value as CriticReview | null;
  if (!review || !keys(review, ['schema', 'request_digest', 'reviewer', 'reviewer_kind', 'counterargument', 'evidence_gaps', 'falsification', 'citations']) || review.schema !== 'research-critic-v1' || !text(review.request_digest, 64) || !/^[a-f0-9]{64}$/.test(review.request_digest) || !text(review.reviewer, 200) || !review.reviewer.trim() || !['HUMAN', 'LLM'].includes(review.reviewer_kind) || !text(review.counterargument, 20000) || !review.counterargument.trim() || !text(review.evidence_gaps, 10000) || !text(review.falsification, 10000) || !Array.isArray(review.citations) || review.citations.length > 50 || review.citations.some(c => !c || !keys(c, ['url', 'published_at']) || !citation(c.url, c.published_at) || !c.url || !c.published_at)) throw new Error('Invalid separately attributed critic review.');
  return review;
}

export function validateWorkspace(value: unknown, earliestAsOf?: string): ResearchWorkspace {
  const data = value as ResearchWorkspace | null;
  if (!data || !keys(data, ['author', 'research_asof', 'qualitative', 'peers', 'time_to_thesis_months', 'time_to_thesis_conditions', 'opportunity_cost', 'critic']) || !text(data.author, 200) || !text(data.research_asof, 100) || !awareTime(data.research_asof) || !text(data.time_to_thesis_months, 3) || (data.time_to_thesis_months !== '' && (!/^\d+$/.test(data.time_to_thesis_months) || Number(data.time_to_thesis_months) < 1 || Number(data.time_to_thesis_months) > 120)) || !text(data.time_to_thesis_conditions) || !text(data.opportunity_cost) || !Array.isArray(data.qualitative) || data.qualitative.length > 50 || !Array.isArray(data.peers) || data.peers.length > 50) throw new Error('Invalid structured research workspace.');
  if (earliestAsOf && (!awareTime(earliestAsOf) || compareTime(data.research_asof, earliestAsOf) < 0)) throw new Error('Research clock predates a selected source. Use a clock at or after its retrieval and financial clocks.');
  const ids = new Set<string>();
  for (const item of data.qualitative) {
    if (!item || !keys(item, ['id', 'category', 'statement', 'kind', 'attribution', 'source_url', 'published_at', 'disconfirmation']) || !text(item.id, 100) || !item.id || ids.has(item.id) || !categories.includes(item.category) || !text(item.statement) || !['PRIMARY_SOURCE_TRANSCRIPTION', 'HUMAN_JUDGMENT', 'LLM_JUDGMENT', 'ASSUMPTION'].includes(item.kind) || !text(item.attribution, 200) || !citation(item.source_url, item.published_at) || !text(item.disconfirmation)) throw new Error('Invalid qualitative evidence record.');
    ids.add(item.id);
  }
  for (const peer of data.peers) {
    if (!peer || !keys(peer, ['id', 'company', 'metric', 'basis', 'currency', 'multiple', 'source_url', 'published_at', 'rationale']) || !text(peer.id, 100) || !peer.id || ids.has(peer.id) || !text(peer.company, 300) || !['P_E', 'EV_REVENUE', 'EV_OPERATING_INCOME'].includes(peer.metric) || !text(peer.basis, 100) || !text(peer.currency, 20) || !text(peer.multiple, 100) || (peer.multiple !== '' && (!/^(?:\d+\.?\d*|\.\d+)$/.test(peer.multiple) || !Number.isFinite(Number(peer.multiple)) || Number(peer.multiple) > 1_000_000)) || !citation(peer.source_url, peer.published_at) || !text(peer.rationale)) throw new Error('Invalid peer valuation record.');
    ids.add(peer.id);
  }
  if (data.critic !== null) parseCritic(data.critic);
  return data;
}

export function evidenceStatus(item: QualitativeItem, asof: string): string {
  if (!awareTime(asof)) return 'INVALID_RESEARCH_CLOCK';
  if (!item.statement.trim() || !item.attribution.trim() || !sourceUrl(item.source_url) || !awareTime(item.published_at)) return 'INCOMPLETE_DATED_SOURCE_OR_ATTRIBUTION';
  if (compareTime(item.published_at, asof) > 0) return 'FUTURE_AT_RESEARCH_CLOCK';
  return item.kind === 'PRIMARY_SOURCE_TRANSCRIPTION' ? 'USER_TRANSCRIPTION_NOT_INDEPENDENTLY_VERIFIED' : 'ATTRIBUTED_JUDGMENT_NOT_VERIFIED_FACT';
}

export function peerBands(workspace: ResearchWorkspace) {
  const groups = new Map<string, number[]>();
  const excluded: {id: string; reason: string}[] = [];
  const signature = (peer: PeerItem) => JSON.stringify([peer.metric, peer.basis, peer.currency, peer.company.trim().replace(/\s+/g, ' ').toLocaleLowerCase('en-US')]);
  const eligibility = (peer: PeerItem): string | null => {
    if (!awareTime(workspace.research_asof)) return 'INVALID_RESEARCH_CLOCK';
    if (!/^(?:\d+\.?\d*|\.\d+)$/.test(peer.multiple) || !Number.isFinite(Number(peer.multiple)) || Number(peer.multiple) > 1_000_000) return 'INVALID_OR_MISSING_MULTIPLE';
    if (!peer.company.trim() || !peer.basis.trim() || !peer.currency.trim() || !peer.rationale.trim() || !sourceUrl(peer.source_url) || !awareTime(peer.published_at)) return 'INCOMPLETE_COMPARISON_OR_DATED_SOURCE';
    if (compareTime(peer.published_at, workspace.research_asof) > 0) return 'FUTURE_AT_RESEARCH_CLOCK';
    return Number(peer.multiple) <= 0 ? 'NONPOSITIVE_MULTIPLE' : null;
  };
  const counts = new Map<string, number>();
  for (const peer of workspace.peers.filter(peer => eligibility(peer) === null)) counts.set(signature(peer), (counts.get(signature(peer)) ?? 0) + 1);
  for (const peer of workspace.peers) {
    const reason = eligibility(peer);
    if (reason) {excluded.push({id: peer.id, reason}); continue;}
    if ((counts.get(signature(peer)) ?? 0) > 1) {excluded.push({id: peer.id, reason: 'DUPLICATE_PEER_COMPANY_IN_COMPARISON'}); continue;}
    const key = JSON.stringify([peer.metric, peer.basis, peer.currency]);
    groups.set(key, [...(groups.get(key) ?? []), Number(peer.multiple)]);
  }
  return {policy: 'peer-comparisons-v1', groups: [...groups].map(([key, values]) => {values.sort((a, b) => a-b); const mid = Math.floor(values.length/2); return {comparison: JSON.parse(key) as string[], count: values.length, minimum: values[0], median: values.length % 2 ? values[mid] : values[mid-1] + (values[mid]-values[mid-1])/2, maximum: values.at(-1)!};}), excluded, status: 'USER_TRANSCRIBED_COMPARISONS_NOT_VALIDATED_FAIR_VALUE'};
}

function canonical(value: unknown): unknown {
  if (value === undefined || ['function', 'symbol', 'bigint'].includes(typeof value) || (typeof value === 'number' && !Number.isFinite(value))) throw new Error('Critic context must contain finite JSON data.');
  if (Array.isArray(value)) return Array.from(value, canonical);
  if (value && typeof value === 'object') {
    if (![Object.prototype, null].includes(Object.getPrototypeOf(value))) throw new Error('Critic context requires plain JSON objects.');
    return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([key, item]) => [key, canonical(item)]));
  }
  return value;
}
export function canonicalContext(value: unknown): string {
  const encoded = JSON.stringify(canonical(value));
  if (encoded === undefined) throw new Error('Critic context must contain JSON data.');
  return encoded;
}
export async function requestDigest(value: unknown): Promise<string> {
  const bytes = new TextEncoder().encode(canonicalContext(value));
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}
export const distinctReviewer = (author: string, reviewer: string) => !!author.trim() && !!reviewer.trim() && author.trim().toLocaleLowerCase('en-US') !== reviewer.trim().toLocaleLowerCase('en-US');
export function researchStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    INCOMPLETE_DATED_SOURCE_OR_ATTRIBUTION: 'Missing dated source or attribution',
    FUTURE_AT_RESEARCH_CLOCK: 'Published after the research clock',
    USER_TRANSCRIPTION_NOT_INDEPENDENTLY_VERIFIED: 'User transcription; not independently verified',
    ATTRIBUTED_JUDGMENT_NOT_VERIFIED_FACT: 'Attributed judgment; not a verified fact',
    INVALID_RESEARCH_CLOCK: 'Enter a valid research clock with a timezone',
    INVALID_OR_MISSING_MULTIPLE: 'Peer multiple is missing or invalid',
    INCOMPLETE_COMPARISON_OR_DATED_SOURCE: 'Comparison details or dated source are missing',
    NONPOSITIVE_MULTIPLE: 'Zero multiple is unresolved and excluded',
    DUPLICATE_PEER_COMPANY_IN_COMPARISON: 'Duplicate peer entries are excluded together',
    NO_CRITIC_ATTACHED: 'No critic review attached',
    STALE_REQUEST: 'Critic review is stale; the research packet changed',
    DISTINCT_ATTRIBUTION_REQUIRED: 'A distinct reviewer attribution is required',
    CRITIC_SOURCES_MISSING: 'Critic sources are missing',
    FUTURE_CRITIC_SOURCE: 'Critic cites a source published after the research clock',
    MATCHES_REQUEST_INDEPENDENCE_NOT_VERIFIED: 'Review matches this packet; independence remains unverified',
  };
  return labels[status] ?? status;
}
export function criticStatus(workspace: ResearchWorkspace, digest: string | null): string {
  if (!awareTime(workspace.research_asof)) return 'INVALID_RESEARCH_CLOCK';
  const critic = workspace.critic;
  if (!critic) return 'NO_CRITIC_ATTACHED';
  if (!digest || critic.request_digest !== digest) return 'STALE_REQUEST';
  if (!distinctReviewer(workspace.author, critic.reviewer)) return 'DISTINCT_ATTRIBUTION_REQUIRED';
  if (!critic.citations.length) return 'CRITIC_SOURCES_MISSING';
  if (critic.citations.some(c => compareTime(c.published_at, workspace.research_asof) > 0)) return 'FUTURE_CRITIC_SOURCE';
  return 'MATCHES_REQUEST_INDEPENDENCE_NOT_VERIFIED';
}

export function researchEvidenceMemo(workspace: ResearchWorkspace, reviewDigest: string | null): string[] {
  const rows = ['', '## Structured primary-source research and attributed judgments', `Research author: ${workspace.author || 'Not supplied'}; research clock: ${workspace.research_asof}.`, 'All entries are operator assertions; source attribution does not independently verify their content.'];
  for (const item of workspace.qualitative) rows.push(`- ${item.category} [${item.kind}; ${evidenceStatus(item, workspace.research_asof)}] ${item.statement}; attribution ${item.attribution || 'missing'}; published ${item.published_at || 'unknown'}; ${item.source_url || 'source missing'}; disconfirmation: ${item.disconfirmation || 'missing'}`);
  rows.push('', '## Peer comparison bands', JSON.stringify(peerBands(workspace)), ...workspace.peers.map(peer => `- ${peer.company}: ${peer.multiple || 'missing'} ${peer.metric}; basis ${peer.basis}; currency ${peer.currency}; published ${peer.published_at || 'unknown'}; ${peer.source_url || 'missing source'}; rationale ${peer.rationale || 'missing'}`), '', '## Time to thesis and opportunity cost', `Horizon assumption: ${workspace.time_to_thesis_months || 'missing'} months; conditions: ${workspace.time_to_thesis_conditions || 'missing'}.`, `Opportunity cost / alternatives: ${workspace.opportunity_cost || 'Not supplied'}`, '', '## Separately attributed critic');
  const critic = workspace.critic;
  if (critic) rows.push(`Reviewer: ${critic.reviewer} (${critic.reviewer_kind}); ${criticStatus(workspace, reviewDigest)}.`, `Counterargument: ${critic.counterargument}`, `Evidence gaps: ${critic.evidence_gaps}`, `Falsification: ${critic.falsification}`, ...critic.citations.map(c => `- ${c.url}; published ${c.published_at}`));
  else rows.push('No separately attributed critic review attached. A bear note or code review does not satisfy this step.');
  return rows;
}
