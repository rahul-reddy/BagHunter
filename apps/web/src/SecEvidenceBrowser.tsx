import { useEffect, useState } from 'react';
import { download } from './downloads';
import { SecFinancialProfile, type FinancialProfile } from './SecFinancialProfile';
import { SecStatements } from './SecStatements';

type Entry = {bundle_id: string; cik: string; asof: string};
type Page = {bundle_id: string; total: number; offset: number; limit: number; source_facts: number;
  financial_profile?: FinancialProfile;
  manifest: {cik: string; asof: string; status: string; lag_hours: number; submissions: {retrieved_at: string}; companyfacts: {retrieved_at: string}};
  normalized: {normalization_policy: string; status: string; identity_assignment: string; excluded_counts: Record<string, number>; limitations: string[];
    submission_history?: {parts: number; metadata_rows: number; usable_metadata_rows: number; missing_primary_document_rows: number};
    facts: {metric: string; value: number; unit: string; period_end: string; accepted_at: string; published_at: string; accession: string; amended: boolean; source_url: string}[]}};

export function SecEvidenceBrowser() {
  const [index, setIndex] = useState<Entry[] | null>(null);
  const [indexError, setIndexError] = useState('');
  const [selection, setSelection] = useState('');
  const [metric, setMetric] = useState('');
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState<{key: string; data: Page} | null>(null);
  const [failure, setFailure] = useState<{key: string; message: string} | null>(null);
  useEffect(() => {const controller = new AbortController(); fetch('/api/sec/bundles', {signal: controller.signal}).then(async response => {
    if (!response.ok) throw new Error('Unable to list local SEC archives.');
    const data = await response.json() as {bundles: Entry[]};
    if (!Array.isArray(data.bundles)) throw new Error('Invalid SEC archive index.');
    if (!controller.signal.aborted) {setIndex(data.bundles); setIndexError('');}
  }).catch((e: Error) => {if (!controller.signal.aborted) setIndexError(e.message);}); return () => controller.abort();}, [revision]);
  const key = JSON.stringify([selection, metric, offset, revision]);
  useEffect(() => {if (!selection) return; const controller = new AbortController();
    const params = new URLSearchParams({metric, offset: String(offset), limit: '8'});
    fetch(`/api/sec/bundles/${selection}?${params}`, {signal: controller.signal}).then(async response => {
      if (!response.ok) throw new Error('Selected SEC evidence failed source verification.');
      const data = await response.json() as Page;
      if (data.bundle_id !== selection) throw new Error('SEC response does not match the selected archive.');
      if (!controller.signal.aborted) setResult({key, data});
    }).catch((e: Error) => {if (!controller.signal.aborted) setFailure({key, message: e.message});}); return () => controller.abort();
  }, [key, selection, metric, offset]);
  const data = result?.key === key ? result.data : null;
  const error = failure?.key === key ? failure.message : null;
  return <section className="panel sec-evidence"><p className="eyebrow">REAL SEC SOURCES · QUARANTINED ENTITY EVIDENCE</p><h2>SEC filing evidence</h2><p>Inspect saved filing facts separately from fictional research. A CIK identifies an SEC filer; it does not verify a Finviz security, share class or historical universe.</p>
    <label>Saved SEC evidence<select aria-label="Saved SEC evidence" value={selection} onChange={e => {setSelection(e.target.value); setMetric(''); setOffset(0);}}><option value="">Choose an archived SEC entity</option>{index?.map(e => <option key={e.bundle_id} value={e.bundle_id}>CIK {e.cik} · {e.asof} · {e.bundle_id.slice(0, 12)}</option>)}</select></label><button className="secondary" onClick={() => setRevision(n => n+1)}>Reload SEC archives</button>
    {indexError && <p role="alert">{indexError}</p>}{index?.length === 0 && <p>No SEC evidence archived yet. Use the documented issuer import to inspect its filing evidence.</p>}
    {!selection ? <p>Choose a local archive. Selection verifies both original source hashes and recomputes normalization without provider requests.</p> : error ? <p role="alert">{error}</p> : !data ? <p role="status">Verifying SEC source archive…</p> : <>
      <p>CIK {data.manifest.cik} · research clock {data.manifest.asof} · {data.source_facts} normalized annual facts. {data.manifest.status}.</p><p>Raw submissions retrieved {data.manifest.submissions.retrieved_at}; aggregate facts retrieved {data.manifest.companyfacts.retrieved_at}. Original extraction vintages are not certified.</p>
      <p>Publication upper bound: later of acceptance and following UTC midnight of the filing day. Processing lag: {data.manifest.lag_hours} hours after that bound. Period end is not a publication date.</p>
      {data.normalized.submission_history && <p>Historical metadata: {data.normalized.submission_history.parts} archived parts · {data.normalized.submission_history.metadata_rows} accession rows · {data.normalized.submission_history.usable_metadata_rows} with document citations · {data.normalized.submission_history.missing_primary_document_rows} missing primary documents. Current downloads do not certify original extraction vintages.</p>}
      {data.financial_profile && <SecFinancialProfile key={data.bundle_id} profile={data.financial_profile} cik={data.manifest.cik} bundleId={data.bundle_id} />}
      <SecStatements key={data.bundle_id} bundleId={data.bundle_id} />
      <label>SEC annual metric<select aria-label="SEC annual metric" value={metric} onChange={e => {setMetric(e.target.value); setOffset(0);}}><option value="">All supported annual metrics</option>{['annual_revenue', 'annual_net_income', 'annual_operating_income', 'annual_operating_cashflow'].map(m => <option key={m}>{m}</option>)}</select></label>
      <p role="status">{data.total ? `Showing ${data.offset+1}–${Math.min(data.offset+data.limit, data.total)} of ${data.total} SEC facts` : 'No facts match this metric.'}</p>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable SEC filing facts"><table><caption className="sr-only">Quarantined real SEC annual filing facts</caption><thead><tr><th>Metric / period end</th><th>Reported amount</th><th>Accepted / publication upper bound</th><th>Filing source</th></tr></thead><tbody>{data.normalized.facts.map(f => <tr key={`${f.accession}-${f.metric}-${f.period_end}`}><td>{f.metric}<small>{f.period_end}</small></td><td>{f.value.toLocaleString('en-US')} {f.unit}</td><td>{f.accepted_at}<small>{f.published_at}</small></td><td><a href={f.source_url} target="_blank" rel="noreferrer">{f.accession} ↗</a>{f.amended && ' · amendment'}</td></tr>)}</tbody></table></div>
      <div className="pagination"><button className="secondary" disabled={!data.offset} onClick={() => setOffset(Math.max(0, offset-data.limit))}>Previous SEC facts</button><button className="secondary" disabled={data.offset+data.limit >= data.total} onClick={() => setOffset(offset+data.limit)}>Next SEC facts</button><button className="secondary" onClick={() => download(`SEC-${data.manifest.cik}-page-${data.offset}.json`, JSON.stringify({bundle_id: data.bundle_id, manifest: data.manifest, normalized: data.normalized, source_facts: data.source_facts, total: data.total, offset: data.offset, limit: data.limit, export_scope: 'CURRENT_PAGE_ONLY'}, null, 2), 'application/json')}>Export current SEC evidence page</button></div>
      <details><summary>SEC exclusions, policy and source limits</summary><p>{data.normalized.normalization_policy}. Identity assignment: {data.normalized.identity_assignment}.</p><ul>{Object.entries(data.normalized.excluded_counts).map(([name, count]) => <li key={name}>{name}: {count}</li>)}{data.normalized.limitations.map(l => <li key={l}>{l}</li>)}</ul></details>
    </>}
  </section>;
}
