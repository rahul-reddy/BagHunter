import { useEffect, useState } from 'react';

type Candidate = { figi: string; ticker: string; name: string; exchCode: string;
  marketSector: string; securityType: string; securityType2: string | null;
  compositeFIGI: string | null; shareClassFIGI: string | null };
type Evidence = { reference_id: string; base_snapshot_id: string; mode: string; retrieved_at: string;
  response_sha256: string; queried: number; population: number; offset: number; flags: string[];
  records: { ticker: string; status: string; candidates: Candidate[]; identity_promoted: false }[] };
const pretty = (value: string) => value.replaceAll('_', ' ');

export function ReferenceEvidence({ baseSnapshotId, mode }: { baseSnapshotId: string; mode: string }) {
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState<{ key: string; evidence: Evidence } | null>(null);
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null);
  const key = JSON.stringify([baseSnapshotId, mode, revision]);
  useEffect(() => {
    if (revision === 0) return;
    const controller = new AbortController();
    fetch('/api/finviz/reference', { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('No valid local reference batch is selected. See docs/REFERENCE.md.');
      const data = await response.json() as Evidence;
      if (data.base_snapshot_id !== baseSnapshotId || data.mode !== mode)
        throw new Error('Reference evidence belongs to a different source selection. Reload observations.');
      return data;
    }).then(evidence => {
      if (!controller.signal.aborted) setResult({ key, evidence });
    }).catch((error: Error) => {
      if (!controller.signal.aborted) setFailure({ key, message: error.message });
    });
    return () => controller.abort();
  }, [key, baseSnapshotId, mode, revision]);
  const evidence = result?.key === key ? result.evidence : null;
  const error = failure?.key === key ? failure.message : null;
  return <section className="reference-evidence" aria-label="Current reference evidence">
    <h3>Current reference evidence</h3>
    <p>Inspect a saved OpenFIGI mapping batch. Candidates describe a later reference lookup, not
      verified identities at the observation time. Finviz identities and security types stay unresolved.</p>
    <button className="secondary" onClick={() => setRevision(value => value + 1)}>Inspect reference evidence</button>
    {error ? <p role="alert">{error}</p> : revision > 0 && !evidence ? <p role="status">Loading saved reference evidence…</p> : null}
    {evidence && <>
      <p className="tag">{evidence.mode === 'FIXTURE' ? 'SYNTHETIC REFERENCE FIXTURE' : 'OPENFIGI · CURRENT CANDIDATES'}</p>
      <p>{evidence.queried} of {evidence.population} observations queried. Alphabetical sample positions
        {' '}{evidence.offset + 1}–{evidence.offset + evidence.queried}. Unqueried observations have no reference evidence here.</p>
      <p>Reference retrieved: {evidence.retrieved_at}. Name matching is unverified; a single result is not identity promotion.</p>
      {evidence.records.map(record => <details key={record.ticker}>
        <summary>{record.ticker} · {pretty(record.status)} · {record.candidates.length} candidates</summary>
        {record.candidates.length === 0 && <p>No candidate metadata returned. This does not prove a security is invalid or delisted.</p>}
        {record.candidates.map(candidate => <div className="reference-candidate" key={candidate.figi}>
          <p>{candidate.name} · provider ticker {candidate.ticker}</p>
          <p>FIGI: {candidate.figi}<br/>Composite FIGI: {candidate.compositeFIGI ?? 'Unknown'}<br/>
            Share class FIGI: {candidate.shareClassFIGI ?? 'Unknown'}</p>
          <p>Reported type: {candidate.securityType} / {candidate.securityType2 ?? 'Unknown'}<br/>
            Provider context: {candidate.exchCode} / {candidate.marketSector}</p>
        </div>)}
      </details>)}
      <details><summary>Reference lineage and limitations</summary>
        <p>Batch <span className="hash">{evidence.reference_id}</span></p>
        <p>Response SHA-256 <span className="hash">{evidence.response_sha256}</span></p>
        <ul>{evidence.flags.map(flag => <li key={flag}>{pretty(flag)}</li>)}</ul>
        <p>Mapping provides no price currency, capitalization scale, archived universe or original filing vintage.</p>
      </details>
    </>}
  </section>;
}
