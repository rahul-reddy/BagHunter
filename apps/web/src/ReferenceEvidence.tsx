import { useEffect, useState } from 'react';

type Candidate = { figi: string; ticker: string; name: string; exchCode: string;
  marketSector: string; securityType: string; securityType2: string | null;
  compositeFIGI: string | null; shareClassFIGI: string | null };
type Evidence = { reference_id: string; base_snapshot_id: string; mode: string; retrieved_at: string;
  response_sha256: string; queried: number; population: number; offset: number; flags: string[];
  records: { ticker: string; status: string; candidates: Candidate[]; identity_promoted: false }[];
  reconciliation: { policy_version: string; report_sha256: string; reference_id: string;
    base_snapshot_id: string; mode: string; flags: string[];
    records: { ticker: string; source_company: string; disposition: string;
      candidates: { figi: string; name_comparison: string; issues: string[];
        shared_identifiers: Record<string, string[]> }[] }[] } };
const pretty = (value: string) => value.replaceAll('_', ' ');

export function ReferenceEvidence({ baseSnapshotId, mode, explicitSelection = false }: { baseSnapshotId: string; mode: string; explicitSelection?: boolean }) {
  const [revision, setRevision] = useState(0);
  const [selectedBatch, setSelectedBatch] = useState('');
  const [batches, setBatches] = useState<{reference_id: string; retrieved_at: string; limit: number}[]>([]);
  useEffect(() => {const controller = new AbortController(); const params = new URLSearchParams({snapshot: baseSnapshotId, mode}); fetch(`/api/finviz/references?${params}`, {signal: controller.signal}).then(async r => {if (r.ok) {const data: unknown = await r.json(); if (Array.isArray(data)) setBatches(data);}}).catch(() => {}); return () => controller.abort();}, [baseSnapshotId, mode]);
  const [result, setResult] = useState<{ key: string; evidence: Evidence } | null>(null);
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null);
  const key = JSON.stringify([baseSnapshotId, mode, revision, selectedBatch, explicitSelection]);
  useEffect(() => {
    if (revision === 0) return;
    const controller = new AbortController();
    const params = new URLSearchParams({snapshot: baseSnapshotId, mode});
    if (selectedBatch) params.set('reference', selectedBatch);
    fetch(explicitSelection || selectedBatch ? `/api/finviz/reference?${params}` : '/api/finviz/reference', { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('No valid local reference batch is selected. See docs/REFERENCE.md.');
      const data = await response.json() as Evidence;
      if (data.base_snapshot_id !== baseSnapshotId || data.mode !== mode)
        throw new Error('Reference evidence belongs to a different source selection. Reload observations.');
      if (!data.reconciliation || data.reconciliation.reference_id !== data.reference_id
        || data.reconciliation.base_snapshot_id !== baseSnapshotId || data.reconciliation.mode !== mode)
        throw new Error('Comparison evidence does not match this reference batch. Reload evidence.');
      return data;
    }).then(evidence => {
      if (!controller.signal.aborted) setResult({ key, evidence });
    }).catch((error: Error) => {
      if (!controller.signal.aborted) setFailure({ key, message: error.message });
    });
    return () => controller.abort();
  }, [key, baseSnapshotId, mode, revision, selectedBatch, explicitSelection]);
  const evidence = result?.key === key ? result.evidence : null;
  const error = failure?.key === key ? failure.message : null;
  return <section className="reference-evidence" aria-label="Current reference evidence">
    <h3>Current reference evidence</h3>
    <p>Inspect a saved OpenFIGI mapping batch. Candidates describe a later reference lookup, not
      verified identities at the observation time. Finviz identities and security types stay unresolved.</p>
    <label>Saved reference batch<select value={selectedBatch} onChange={e => {setSelectedBatch(e.target.value); setRevision(0);}}><option value="">Use configured reference selection</option>{batches.map(b => <option key={b.reference_id} value={b.reference_id}>{b.retrieved_at} · {b.limit} queried · {b.reference_id.slice(0, 12)}</option>)}</select></label>
    <button className="secondary" onClick={() => setRevision(value => value + 1)}>Inspect reference evidence</button>
    {error ? <p role="alert">{error}</p> : revision > 0 && !evidence ? <p role="status">Loading saved reference evidence…</p> : null}
    {evidence && <>
      <p className="tag">{evidence.mode === 'FIXTURE' ? 'SYNTHETIC REFERENCE FIXTURE' : 'OPENFIGI · CURRENT CANDIDATES'}</p>
      <p>{evidence.queried} of {evidence.population} observations queried. Alphabetical sample positions
        {' '}{evidence.offset + 1}–{evidence.offset + evidence.queried}. Unqueried observations have no reference evidence here.</p>
      <p>Reference retrieved: {evidence.retrieved_at}. Name matching is unverified; a single result is not identity promotion.</p>
      <p>Company and share-class comparison: case and whitespace comparisons only. Punctuation, legal suffixes
        and class labels are preserved. Every candidate requires independent company and share-class evidence.
        Shared identifiers are checked within this batch only and may represent aliases.</p>
      {evidence.records.map(record => {
        const comparison = evidence.reconciliation.records.find(row => row.ticker === record.ticker);
        return <details key={record.ticker}>
        <summary>{record.ticker} · {pretty(record.status)} · {record.candidates.length} {record.candidates.length === 1 ? 'candidate' : 'candidates'}</summary>
        <p>Finviz company: {comparison?.source_company ?? 'Comparison unavailable'}</p>
        <p>Disposition: {comparison ? pretty(comparison.disposition) : 'REVIEW REQUIRED'}. Identity and share class remain unverified.</p>
        {record.candidates.length === 0 && <p>No candidate metadata returned. This does not prove a security is invalid or delisted.</p>}
        {record.candidates.map(candidate => {
          const assessment = comparison?.candidates.find(row => row.figi === candidate.figi);
          return <div className="reference-candidate" key={candidate.figi}>
          <p>OpenFIGI name: {candidate.name} · provider ticker {candidate.ticker}</p>
          <p>Name comparison: {assessment ? pretty(assessment.name_comparison) : 'Unavailable; review required'}.
            Text agreement does not verify identity.</p>
          <p>FIGI: {candidate.figi}<br/>Composite FIGI: {candidate.compositeFIGI ?? 'Unknown'}<br/>
            Share class FIGI: {candidate.shareClassFIGI ?? 'Unknown'}</p>
          <p>Reported type: {candidate.securityType} / {candidate.securityType2 ?? 'Unknown'}<br/>
            Provider context: {candidate.exchCode} / {candidate.marketSector}</p>
          {assessment && <>
            <ul>{assessment.issues.map(issue => <li key={issue}>{pretty(issue)}</li>)}</ul>
            {Object.entries(assessment.shared_identifiers).map(([field, tickers]) =>
              <p key={field}>{field} also reported for: {tickers.join(', ')} (this batch only)</p>)}
          </>}
        </div>; })}
      </details>; })}
      <details><summary>Reference lineage and limitations</summary>
        <p>Batch <span className="hash">{evidence.reference_id}</span></p>
        <p>Response SHA-256 <span className="hash">{evidence.response_sha256}</span></p>
        <p>Comparison policy: {evidence.reconciliation.policy_version}<br/>
          Comparison SHA-256 <span className="hash">{evidence.reconciliation.report_sha256}</span></p>
        <ul>{evidence.reconciliation.flags.map(flag => <li key={flag}>{pretty(flag)}</li>)}</ul>
        <ul>{evidence.flags.map(flag => <li key={flag}>{pretty(flag)}</li>)}</ul>
        <p>Mapping provides no price currency, capitalization scale, archived universe or original filing vintage.</p>
      </details>
    </>}
  </section>;
}
