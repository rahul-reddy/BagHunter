import {ResearchEvidence, useResearchDigest} from './ResearchEvidencePanel';
import {emptyWorkspace, criticStatus, peerBands, validateWorkspace, awareTime, compareTime} from './researchEvidence';
import {useCallback, useState} from 'react';
import type {Observation} from './FinvizBrowser';
import {download} from './downloads';
import {CompanyEvidencePicker, type CompanyEvidence} from './CompanyEvidence';
import {ObservationScenarios} from './ObservationScenarios';
import {emptyAssumptions, emptyNotes, observationMemo, restoreResearch, type CompanyScenario, type ObservationSource, type ObservationNotes} from './observationResearch';

const labels: Record<keyof ObservationNotes, string> = {hypothesis: 'Observation research hypothesis', evidence: 'Sources and unresolved research questions', falsification: 'Observation falsification conditions', bear: 'Observation bear argument', review_date: 'Observation review date'};

export function ObservationDesk({observation, source, onClose}: {observation: Observation; source: ObservationSource; onClose: () => void}) {
  const storageKey = `baghunter.observation.v1.${source.mode}.${source.snapshot_id}.${observation.ticker}`;
  const [workspace, setWorkspace] = useState(() => emptyWorkspace(new Date().toISOString()));
  const [draft, setDraft] = useState<ObservationNotes>({...emptyNotes});
  const [inputs, setInputs] = useState({...emptyAssumptions});
  const [bundleId, setBundleId] = useState('');
  const [evidence, setEvidence] = useState<CompanyEvidence | null>(null);
  const [evidenceRevision, setEvidenceRevision] = useState(0);
  const [calculation, setCalculation] = useState<{key: string; scenarios: CompanyScenario[]} | null>(null);
  const [message, setMessage] = useState('');
  const onVerified = useCallback((value: CompanyEvidence | null) => {setEvidence(value); if (!value) setCalculation(null);}, []);
  const attached = source.mode !== 'FIXTURE' && evidence?.bundle_id === bundleId ? evidence : null;
  const ready = !bundleId || !!attached;
  const contextKey = JSON.stringify([source.mode, source.snapshot_id, source.source_sha256, observation.ticker, bundleId, ready]);
  const calculationKey = JSON.stringify([contextKey, inputs]);
  const scenarios = ready && calculation?.key === calculationKey ? calculation.scenarios : null;
  const sourceClocks = [source.retrieved_at, ...(attached ? [attached.manifest.asof, attached.manifest.submissions.retrieved_at, attached.manifest.companyfacts.retrieved_at] : [])];
  const minimumResearchClock = sourceClocks.every(awareTime) ? sourceClocks.reduce((left, right) => compareTime(left, right) < 0 ? right : left) : '';
  let workspaceIssue = '';
  try {if (!minimumResearchClock) throw new Error('Selected source clock is unavailable.'); validateWorkspace(workspace, minimumResearchClock);} catch (error) {workspaceIssue = (error as Error).message;}
  const exportReady = ready && !workspaceIssue;
  const criticContext = {source, observation, draft, scenario_assumptions: inputs, scenarios, sec_bundle_id: bundleId, issuer_evidence: attached, workspace: {...workspace, critic: null}};
  const reviewDigest = useResearchDigest(criticContext);
  const prefix = `${source.mode === 'FIXTURE' ? 'FIXTURE' : 'UNVERIFIED'}-${observation.ticker}`;
  const sourceContext = {mode:source.mode, snapshot_id:source.snapshot_id, ticker:observation.ticker};
  const save = () => {
    if (workspaceIssue) {setMessage(`Cannot save research draft: ${workspaceIssue}`); return;}
    const payload = {schema:'observation-research-v3', source_sha256:source.source_sha256, source_context:sourceContext, draft, sec_bundle_id:bundleId, scenario_assumptions:inputs, research_workspace:workspace};
    try {validateWorkspace(workspace, minimumResearchClock); restoreResearch(payload, source.source_sha256, sourceContext);}
    catch (error) {setMessage(`Cannot save research draft: ${(error as Error).message}`); return;}
    try {localStorage.setItem(storageKey, JSON.stringify(payload)); setMessage('Observation draft saved for this exact snapshot and ticker. Evidence and calculations are reverified when loaded.');}
    catch {setMessage('Browser storage unavailable. Export the dossier to preserve this draft.');}
  };
  const load = () => {
    try {
      const restored = restoreResearch(JSON.parse(localStorage.getItem(storageKey) ?? 'null'), source.source_sha256, sourceContext);
      if (source.mode === 'FIXTURE' && restored.bundleId) throw new Error('Real entity attachment cannot be loaded into a fixture observation.');
      const restoredWorkspace = restored.workspace ?? emptyWorkspace(new Date().toISOString());
      // The saved issuer re-verifies after loading; the currently selected issuer is unrelated.
      validateWorkspace(restoredWorkspace, source.retrieved_at);
      setWorkspace(restoredWorkspace); setDraft(restored.draft); setInputs(restored.inputs); setBundleId(restored.bundleId);
      setEvidence(null); setCalculation(null); setEvidenceRevision(value => value+1);
      setMessage('Saved source-bound observation draft loaded. Attached evidence must reverify; scenarios require recalculation.');
    } catch {setMessage('No valid draft matches this observation and source checksum.');}
  };
  const dossier = () => ({schema:'observation-research-v3', status:'USER_ASSERTIONS_NOT_VERIFIED_THESIS', source, observation, draft,
    research_workspace: workspace, critic_status: criticStatus(workspace, reviewDigest), peer_comparisons: peerBands(workspace), scenario_assumptions:inputs, scenarios,
    issuer_evidence:attached ? {association_status:'OPERATOR_SELECTED_ENTITY_NOT_VERIFIED_SECURITY_MAPPING', ...attached} : null,
    limitations:['Current saved observation only; not historical PIT evidence', 'SEC attachment is an operator research association, not a security/class assignment', 'Source clocks remain separate; no merged PIT profile', 'No permanent identity, eligibility approval or ranking', 'Financial model inputs are user assumptions, not forecasts', 'Reported Finviz values retain provider scale; no automatic USD or share conversion']});
  return <section className="panel company-research" aria-label={`Research workspace for observation ${observation.ticker}`}>
    <div className="panel-title"><div><p className="eyebrow">{source.mode} · CURRENT OBSERVATION · UNVERIFIED</p><h2>{observation.ticker} · Observation research desk</h2><p>{observation.company}. This is a source-bound research draft, with no assigned permanent identity or screening score.</p></div><button className="secondary" onClick={onClose}>Close observation desk</button></div>
    <p>Retrieved {source.retrieved_at}. Provider observation time is unknown. Reported price, market-cap scale, currency, security type and historical continuity are unverified.</p>
    <dl><dt>Snapshot</dt><dd className="hash">{source.snapshot_id}</dd><dt>Original CSV SHA-256</dt><dd className="hash">{source.source_sha256}</dd></dl>
    <div className="input-grid">{(Object.keys(emptyNotes) as (keyof ObservationNotes)[]).map(name => <label key={name}>{labels[name]}{name === 'review_date' ? <input type="date" value={draft[name]} onChange={event => setDraft({...draft, [name]:event.target.value})}/> : <textarea aria-label={labels[name]} maxLength={5000} value={draft[name]} onChange={event => setDraft({...draft, [name]:event.target.value})}/>}</label>)}</div>
    {source.mode !== 'FIXTURE' && <CompanyEvidencePicker key={evidenceRevision} bundleId={bundleId} onSelect={id => {setBundleId(id); setEvidence(null); setCalculation(null);}} onVerified={onVerified} onUseRevenue={value => {setInputs({...inputs, revenue:String(value)}); setCalculation(null); setMessage('Selected SEC annual revenue copied as your starting assumption. Security association, class shares and USD applicability remain unverified.');}}/>}
    <ObservationScenarios inputs={inputs} onInputs={next => {setInputs(next); setCalculation(null);}} contextKey={contextKey} enabled={ready} onCalculated={(key, values) => setCalculation(values.length ? {key, scenarios:values} : null)} results={scenarios}/>
    <ResearchEvidence workspace={workspace} onChange={setWorkspace} context={criticContext} digest={reviewDigest} enabled={exportReady}/>
    {workspaceIssue && <p role="alert">Structured research needs correction: {workspaceIssue}</p>}
    <div className="button-row"><button className="secondary" onClick={save}>Save observation draft</button><button className="secondary" onClick={load}>Load observation draft</button><button className="secondary" disabled={!exportReady} onClick={() => download(`${prefix}-research.json`, JSON.stringify(dossier(), null, 2), 'application/json')}>Export observation dossier</button><button className="secondary" disabled={!exportReady} onClick={() => download(`${prefix}-memo.md`, observationMemo(source, observation, draft, attached, scenarios, workspace, reviewDigest), 'text/markdown')}>Export observation research memo</button></div>
    <p role="status">{message}</p><p>Notes, selected archive ID and assumption inputs persist only when saved. A different snapshot has a separate draft. Evidence is reverified and calculations are cleared on load. Exports preserve separate sources and user assertions without activating research inputs.</p>
  </section>;
}
