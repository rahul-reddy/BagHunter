import { useState } from 'react';
import type { Observation } from './FinvizBrowser';
import { download } from './downloads';

type Source = {mode: string; snapshot_id: string; source_sha256: string; retrieved_at: string};
const blank = {hypothesis: '', evidence: '', falsification: '', bear: '', review_date: ''};
type Draft = typeof blank;
const labels: Record<keyof Draft, string> = {hypothesis: 'Observation research hypothesis', evidence: 'Sources and unresolved research questions', falsification: 'Observation falsification conditions', bear: 'Observation bear argument', review_date: 'Observation review date'};

export function ObservationDesk({observation, source, onClose}: {observation: Observation; source: Source; onClose: () => void}) {
  // A snapshot/ticker pair identifies an observation, never a permanent security.
  const storageKey = `baghunter.observation.v1.${source.mode}.${source.snapshot_id}.${observation.ticker}`;
  const [draft, setDraft] = useState<Draft>(blank);
  const [message, setMessage] = useState('');
  const save = () => {try {localStorage.setItem(storageKey, JSON.stringify({source_sha256: source.source_sha256, draft})); setMessage('Observation draft saved for this exact snapshot and ticker.');} catch {setMessage('Browser storage unavailable. Export the dossier to preserve this draft.');}};
  const load = () => {try {
    const saved = JSON.parse(localStorage.getItem(storageKey) ?? 'null');
    if (!saved || saved.source_sha256 !== source.source_sha256 || !saved.draft || Object.keys(saved.draft).length !== Object.keys(blank).length || Object.keys(blank).some(k => typeof saved.draft[k] !== 'string' || saved.draft[k].length > 5000)) throw new Error();
    const date = saved.draft.review_date;
    if (date && (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isFinite(Date.parse(date)) || new Date(date).toISOString().slice(0, 10) !== date)) throw new Error();
    setDraft(saved.draft); setMessage('Saved source-bound observation draft loaded.');
  } catch {setMessage('No valid draft matches this observation and source checksum.');}};
  return <section className="panel" aria-label={`Research workspace for observation ${observation.ticker}`}>
    <div className="panel-title"><div><p className="eyebrow">{source.mode} · CURRENT OBSERVATION · UNVERIFIED</p><h2>{observation.ticker} · Observation research desk</h2><p>{observation.company}. This is a source-bound research draft, with no assigned permanent identity or screening score.</p></div><button className="secondary" onClick={onClose}>Close observation desk</button></div>
    <p>Retrieved {source.retrieved_at}. Provider observation time is unknown. Reported price, market-cap scale, currency, security type and historical continuity are unverified.</p>
    <dl><dt>Snapshot</dt><dd className="hash">{source.snapshot_id}</dd><dt>Original CSV SHA-256</dt><dd className="hash">{source.source_sha256}</dd></dl>
    <div className="input-grid">{(Object.keys(blank) as (keyof Draft)[]).map(k => <label key={k}>{labels[k]}{k === 'review_date' ? <input type="date" value={draft[k]} onChange={e => setDraft({...draft, [k]: e.target.value})}/> : <textarea aria-label={labels[k]} maxLength={5000} value={draft[k]} onChange={e => setDraft({...draft, [k]: e.target.value})}/>}</label>)}</div>
    <div className="button-row"><button className="secondary" onClick={save}>Save observation draft</button><button className="secondary" onClick={load}>Load observation draft</button><button className="secondary" onClick={() => download(`${source.mode === 'FIXTURE' ? 'FIXTURE' : 'UNVERIFIED'}-${observation.ticker}-research.json`, JSON.stringify({schema: 'observation-research-v1', status: 'USER_ASSERTIONS_NOT_VERIFIED_THESIS', source, observation, draft, limitations: ['Current saved observation only; not historical PIT evidence', 'No permanent identity, security-type approval or ranking', 'Draft assertions and cited text require independent verification', 'Reported values retain provider scale; no currency conversion']}, null, 2), 'application/json')}>Export observation dossier</button></div>
    <p role="status">{message}</p><p>Notes persist only when saved. A different snapshot has a separate draft. Export preserves the original reported values and provenance without activating research inputs.</p>
  </section>;
}
