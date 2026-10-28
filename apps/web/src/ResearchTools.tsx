import {RobustnessLab} from './RobustnessLab';
import { useEffect, useRef, useState } from 'react';
import type { Run, Signal } from './main';
import { download } from './downloads';
import { CatalystCalendar, type Catalyst } from './CatalystCalendar';
import {ResearchEvidence, useResearchDigest} from './ResearchEvidencePanel';
import {emptyWorkspace, criticStatus, peerBands, riskRegister, researchEvidenceMemo, validateWorkspace} from './researchEvidence';
import {initialThesisInputs, parseThesisInputs, restoreThesisDraft, validateThesisNotes, type ThesisInputs} from './thesisDraft';
import { PortfolioComparisons } from './PortfolioComparisons';
import { DailyRiskPanel } from './DailyRiskPanel';
import { RankingSensitivity } from './RankingSensitivity';
import { NegativeControls } from './NegativeControls';

export const percent = (v: number | null | undefined) => v == null ? 'Missing' : `${(v * 100).toFixed(2)}%`;
const number = (v: number) => v.toLocaleString('en-US', {maximumFractionDigits: 2});

export function PriceChart({candidate}: {candidate: Signal}) {
  const points = candidate.chart;
  if (!points.length) return <p>No known chart observations.</p>;
  const min = Math.min(...points.map(p => p.close), candidate.base_high_60d);
  const max = Math.max(...points.map(p => p.close), candidate.base_high_60d);
  const x = (i: number) => 55 + i / Math.max(1, points.length - 1) * 735;
  const y = (value: number) => 190 - (value-min) / (max-min || 1) * 170;
  const volumeMax = Math.max(1, ...points.map(p => p.volume ?? 0));
  const markers = candidate.stage_history?.filter(h => ['IGNITION', 'CONFIRMED', 'INVALIDATED'].includes(h.stage)) ?? [];
  return <figure className="chart"><svg viewBox="0 0 810 310" role="img" aria-label={`${candidate.ticker} known raw fixture prices, current prior-60-session base high and stage markers`}>
    {[0, 1, 2, 3].map(i => <g key={i}><line x1="55" x2="790" y1={20+i*55} y2={20+i*55} stroke="#33434d" strokeDasharray="3 5"/><text x="0" y={25+i*55} fill="#b8cbd4" fontSize="12">{(max-(max-min)*i/3).toFixed(2)}</text></g>)}
    <line x1="55" x2="790" y1={y(candidate.base_high_60d)} y2={y(candidate.base_high_60d)} stroke="#e5b56a" strokeDasharray="6 4"/>
    <polyline fill="none" stroke="#75e4cd" strokeWidth="2.5" points={points.map((p, i) => `${x(i)},${y(p.close)}`).join(' ')}/>
    {points.map((p, i) => <rect key={p.date} x={x(i)} y={285-(p.volume ?? 0)/volumeMax*55} width="3" height={(p.volume ?? 0)/volumeMax*55} fill="#688e9f"/>)}
    {markers.map(h => {const i = points.findIndex(p => p.date === h.session); return i < 0 || h.close == null ? null : <circle key={h.asof} cx={x(i)} cy={y(h.close)} r="4" fill={h.stage === 'INVALIDATED' ? '#f0a49e' : '#e5b56a'}><title>{h.session}: {h.stage} · {h.reason}</title></circle>;})}
    <text x="55" y="307" fill="#b8cbd4" fontSize="11">{points[0].date}</text><text x="670" y="307" fill="#b8cbd4" fontSize="11">{points.at(-1)?.date}</text>
  </svg><figcaption>FIXTURE raw USD prices and known volume · dashed amber: current prior-60-session base high (reference line, not historical base history). Dots: ignition, confirmation or invalidation. As-of {candidate.asof_time}; raw adjustment basis.</figcaption></figure>;
}


export type Preferences = { watchlist: string[]; minLiquidity: number; minCoverage: number; sector: string; watchOnly: boolean };
const defaults: Preferences = {watchlist: [], minLiquidity: 0, minCoverage: 0, sector: 'ALL', watchOnly: false};
export function usePreferences(): [Preferences, (next: Preferences) => void, string] {
  const [error, setError] = useState('');
  const [value, setValue] = useState<Preferences>(() => {
    try {
      const raw = JSON.parse(localStorage.getItem('baghunter.preferences.v1') ?? 'null');
      if (!raw || !Array.isArray(raw.watchlist) || !raw.watchlist.every((s: unknown) => typeof s === 'string') ||
          !Number.isFinite(raw.minLiquidity) || raw.minLiquidity < 0 || !Number.isFinite(raw.minCoverage) ||
          raw.minCoverage < 0 || raw.minCoverage > 1 || typeof raw.sector !== 'string' || typeof raw.watchOnly !== 'boolean') return defaults;
      return raw as Preferences;
    } catch { return defaults; }
  });
  return [value, next => {
    setValue(next);
    try { localStorage.setItem('baghunter.preferences.v1', JSON.stringify(next)); setError(''); }
    catch { setError('Browser storage unavailable. Preferences apply to this session only.'); }
  }, error];
}

type ScenarioResult = {per_share_value: number; annualized_change: number; diluted_shares: number; enterprise_value: number};
const initial = initialThesisInputs;
const labels: Record<keyof ThesisInputs, string> = {revenue: 'Starting revenue (USD assumption)', shares: 'Starting shares (assumption)', net_debt: 'Net debt (USD; negative means net cash)', reference_price: 'Reference price (USD assumption)', years: 'Scenario horizon (years)', dilution: 'Annual dilution (fraction)', growth: 'Annual revenue growth (fraction)', margin: 'Operating margin (fraction)', multiple: 'EV / operating earnings multiple'};

export function ThesisStudio({candidate, run}: {candidate: Signal; run: Run}) {
  const [inputs, setInputs] = useState<ThesisInputs>(initial);
  const [calculation, setCalculation] = useState<{key: string; values: {name: string; value: ScenarioResult}[]} | null>(null);
  const results = calculation?.key === JSON.stringify(inputs) ? calculation.values : [];
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [thesis, setThesis] = useState('');
  const [catalyst, setCatalyst] = useState('');
  const [breaker, setBreaker] = useState('');
  const [bear, setBear] = useState('');
  const [saved, setSaved] = useState('');
  const [monitorDate, setMonitorDate] = useState('');
  const [workspace, setWorkspace] = useState(() => emptyWorkspace(new Date().toISOString()));
  const [calendar, setCalendar] = useState<Catalyst[] | null>(null);
  const sourceContext = {mode:run.mode,run_id:run.run_id,security_id:candidate.security_id,source_sha256s:run.sources.map(source => source.sha256)};
  const storageKey = `baghunter.memo.v2.${run.run_id}.${candidate.security_id}`;
  const notes = {thesis,catalyst,breaker,bear,monitorDate};
  let workspaceIssue = '';
  try {validateWorkspace(workspace,run.asof);validateThesisNotes(notes);parseThesisInputs(inputs);} catch (e) {workspaceIssue = (e as Error).message;}
  const criticContext = {schema:'fixture-thesis-context-v1',source_context:sourceContext,asof:run.asof,model_version:run.model_version,sources:run.sources,candidate,assumptions:inputs,scenarios:results,notes,catalyst_calendar:calendar,workspace:{...workspace,critic:null}};
  const reviewDigest = useResearchDigest(criticContext);
  const exportReady = calendar !== null && !busy && results.length === 3 && !workspaceIssue;

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setBusy(true); setError(''); setCalculation(null);
      let numeric: ReturnType<typeof parseThesisInputs>;
      try {numeric = parseThesisInputs(inputs);} catch (e) {setError((e as Error).message);setBusy(false);return;}
      const variants = [{name: 'Bear', growth: numeric.growth - .1, margin: numeric.margin - .05, multiple: Math.max(0, numeric.multiple - 5)},
        {name: 'Base', growth: numeric.growth, margin: numeric.margin, multiple: numeric.multiple},
        {name: 'Bull', growth: numeric.growth + .1, margin: numeric.margin + .05, multiple: numeric.multiple + 5}];
      Promise.all(variants.map(async variant => {
        const params = new URLSearchParams(Object.entries({...numeric, growth: variant.growth, margin: variant.margin, multiple: variant.multiple}).map(([k, v]) => [k, String(v)]));
        const response = await fetch(`/api/scenario?${params}`, {signal: controller.signal});
        if (!response.ok) throw new Error('Scenario inputs are outside supported bounds. Check positive revenue, shares, price and a 1–10 year horizon.');
        return {name: variant.name, value: await response.json() as ScenarioResult};
      })).then(values => {if (!controller.signal.aborted) setCalculation({key: JSON.stringify(inputs), values});}).catch((e: Error) => {if (e.name !== 'AbortError') setError(e.message);})
        .finally(() => {if (!controller.signal.aborted) setBusy(false);});
    }, 250);
    return () => {clearTimeout(timer); controller.abort();};
  }, [inputs]);
  const memo = () => `# FIXTURE / USER ASSUMPTIONS — ${candidate.ticker}\n\nRun ${run.run_id}; as-of ${run.asof}. Not a verified thesis or investment forecast.\n\n## Hypothesis\n${thesis || 'Not entered'}\n\n## Assumptions\n${JSON.stringify(inputs, null, 2)}\n\nBear/base/bull offsets: growth -/+ 10 percentage points; operating margin -/+ 5 points; multiple -/+ 5, floored at zero. No probabilities. Net debt held constant.\n\n## Scenario arithmetic\n${results.map(r => `${r.name}: USD ${r.value.per_share_value.toFixed(2)} per diluted share; annualized change ${percent(r.value.annualized_change)}`).join('\n')}\n\n## Dated filing evidence (synthetic)\n${candidate.evidence.map(f => `- ${f.metric}, ${f.period_end}: ${f.value}; first public ${f.published_at}; source ${f.source_id}; accession ${f.accession}`).join('\n')}\n\n## Catalyst checklist\n${catalyst || 'None supplied'}\nReview date: ${monitorDate || 'Not set'}\n\n## Falsification monitor\n${breaker || 'Not supplied'}\n\n## Bear argument / alternative explanation\n${bear || 'Independent critique not supplied'}\n\n## Unresolved risks\nLiquidity, dilution, competition, refinancing, source coverage and model uncertainty require evidence. ${workspace.critic ? "See separately attributed critic status below; independence remains unverified." : "No separately attributed critic is attached."} Zero real verified theses.\n` + researchEvidenceMemo(workspace,reviewDigest).join('\n') + `\n\n## Dated catalyst assertions\n${JSON.stringify(calendar,null,2)}\n`;
  const save = () => {
    if (workspaceIssue) {setSaved(`Cannot save thesis draft: ${workspaceIssue}`);return;}
    try {localStorage.setItem(storageKey, JSON.stringify({schema:'fixture-thesis-draft-v2',source_context:sourceContext,inputs,notes,research_workspace:workspace})); setSaved('Draft saved for this exact run and security in this browser.');}
    catch {setSaved('Unable to save. Download the memo or dossier to preserve your work.');}
  };
  const load = () => {
    try {
      const raw = localStorage.getItem(storageKey) ?? localStorage.getItem(`baghunter.memo.${candidate.security_id}`);
      const draft = restoreThesisDraft(JSON.parse(raw ?? 'null'),sourceContext,run.asof);
      setCalculation(null);setInputs(draft.inputs);setWorkspace(draft.workspace);setThesis(draft.notes.thesis);setCatalyst(draft.notes.catalyst);setBreaker(draft.notes.breaker);setBear(draft.notes.bear);setMonitorDate(draft.notes.monitorDate);
      setSaved(draft.legacy ? 'Legacy unbound notes and assumptions loaded; no sources or critic restored. Save a run-bound draft.' : 'Run-bound draft loaded; scenarios recalculate and critic status is rechecked against the current calendar.');
    } catch (e) {setSaved(`Cannot load thesis draft: ${(e as Error).message}`);}
  };
  const dossier = () => ({schema:'fixture-thesis-dossier-v2',mode:'FIXTURE_USER_ASSUMPTIONS',source_context:sourceContext,asof:run.asof,model_version:run.model_version,sources:run.sources,candidate,assumptions:inputs,scenarios:results,notes,catalyst_calendar:calendar,research_workspace:workspace,peer_comparisons:peerBands(workspace),risk_register:riskRegister(workspace),critic_status:criticStatus(workspace,reviewDigest),request_digest:reviewDigest,verified_real_theses:0});
  return <>
    <section className="panel"><div className="panel-title"><div><p className="eyebrow">ASSUMPTIONS WORKBENCH</p><h2>{candidate.ticker} · Thesis Studio</h2><p>Illustrative defaults are user assumptions, not company financials. No probabilities or verified investment thesis.</p></div><button className="secondary" disabled={!exportReady} onClick={() => download(`FIXTURE-${candidate.security_id}-memo.md`, memo())}>Download thesis memo</button></div>
      <div className="input-grid">{(Object.keys(initial) as (keyof ThesisInputs)[]).map(k => <label key={k}>{labels[k]}<input type="number" step="any" value={inputs[k]} onChange={e => {setCalculation(null); setInputs({...inputs, [k]: e.target.value});}} /></label>)}</div>
      <p>Bear/base/bull offsets: growth ±10 percentage points, margin ±5 points, multiple ±5 (floor zero). All three scenarios share dilution and net debt assumptions.</p>
      {busy && <p role="status">Calculating assumption scenarios…</p>}{error && !workspaceIssue && <p role="alert">{error}</p>}
      <div className="scenario-grid">{results.map(r => <article className="scenario-card" key={r.name}><h3>{r.name} scenario</h3><strong>${number(r.value.per_share_value)}</strong><p>Per diluted share, USD assumption</p><p>Annualized change {percent(r.value.annualized_change)}</p><p>Ending shares {number(r.value.diluted_shares)}</p></article>)}</div>
      <p className="footnote">EV = revenue × (1+growth)^years × operating margin × earnings multiple. Equity = max(0, EV − net debt). Divide by shares × (1+dilution)^years. No dividends, taxes or discounting modeled.</p>
    </section>
    <CatalystCalendar key={candidate.security_id} securityId={candidate.security_id} ticker={candidate.ticker} onChange={setCalendar} />
    <section className="panel"><ResearchEvidence workspace={workspace} onChange={setWorkspace} context={criticContext} digest={reviewDigest} enabled={exportReady}/>{workspaceIssue && <p role="alert">Thesis research needs correction: {workspaceIssue}</p>}<button className="secondary" disabled={!exportReady} onClick={() => download(`FIXTURE-${candidate.security_id}-dossier.json`,JSON.stringify(dossier(),null,2),'application/json')}>Download thesis dossier</button></section>
    <section className="panel"><h2>Research memo & falsification monitor</h2><div className="input-grid"><label>Research hypothesis<textarea aria-label="Research hypothesis" maxLength={5000} value={thesis} onChange={e => setThesis(e.target.value)} /></label><label>Catalysts and source citations<textarea aria-label="Catalysts and source citations" maxLength={5000} value={catalyst} onChange={e => setCatalyst(e.target.value)} /></label><label>Falsification conditions<textarea aria-label="Falsification conditions" maxLength={5000} value={breaker} onChange={e => setBreaker(e.target.value)} /></label><label>Bear argument and alternative explanation<textarea aria-label="Bear argument and alternative explanation" maxLength={5000} value={bear} onChange={e => setBear(e.target.value)} /></label><label>Next catalyst review date<input type="date" value={monitorDate} onChange={e => setMonitorDate(e.target.value)} /></label></div><div className="button-row"><button className="secondary" onClick={save}>Save draft locally</button><button className="secondary" onClick={load}>Load saved draft</button></div><p role="status">{saved}</p><p>Draft assertions require source verification and an independent critic. Notes do not change scores or research evidence.</p></section>
  </>;
}

export function ValidationTools({run}: {run: Run}) {
  const [tradeSecurity, setTradeSecurity] = useState('ALL');
  const [tradeYear, setTradeYear] = useState('ALL');
  const [tradePage, setTradePage] = useState(0);
  const executions = run.portfolio?.executions ?? [];
  const filteredTrades = executions.filter(e => (tradeSecurity === 'ALL' || e.security_id === tradeSecurity) && (tradeYear === 'ALL' || e.decision.startsWith(tradeYear)));
  const currentPage = Math.min(tradePage, Math.max(0, Math.ceil(filteredTrades.length / 12) - 1));
  const v = run.validation;
  if (!v) return <section className="panel"><h2>Validation diagnostics unavailable</h2><p>Rebuild this archived run to materialize the diagnostics.</p></section>;
  return <><NegativeControls discoveryData={v.discovery_negative_controls} data={v.negative_controls} runId={run.run_id}/><RankingSensitivity data={run.discovery?.sensitivity} runId={run.run_id}/><DailyRiskPanel run={run} /><RobustnessLab key={run.run_id} report={v.robustness} runId={run.run_id}/><PortfolioComparisons comparisons={run.portfolio?.comparator_runs} runId={run.run_id} />{run.portfolio && <section className="panel"><h2>Constrained portfolio simulation</h2><p>FIXTURE · long only, no leverage. Starting capital ${number(run.portfolio.policy.capital)}; position cap {percent(run.portfolio.policy.max_position)}, sector cap {percent(run.portfolio.policy.max_sector)}, known-dollar-volume participation cap {percent(run.portfolio.policy.participation)}. One-way costs {run.portfolio.policy.one_way_cost_bps} bps. Unused capital stays in cash.</p><p>Ending equity ${number(run.portfolio.ending_equity)} · net return {percent(run.portfolio.metrics.total_return)} · window-end drawdown {percent(run.portfolio.metrics.max_drawdown)}.</p><div className="filters"><label>Execution security<select value={tradeSecurity} onChange={e => {setTradeSecurity(e.target.value); setTradePage(0);}}><option value="ALL">All securities</option>{[...new Set(executions.map(e => e.security_id))].map(s => <option key={s}>{s}</option>)}</select></label><label>Execution year<select value={tradeYear} onChange={e => {setTradeYear(e.target.value); setTradePage(0);}}><option value="ALL">All years</option>{[...new Set(executions.map(e => e.decision.slice(0, 4)))].map(y => <option key={y}>{y}</option>)}</select></label></div><p role="status">{filteredTrades.length ? `Showing ${currentPage*12+1}–${Math.min((currentPage+1)*12, filteredTrades.length)} of ${filteredTrades.length} executions` : 'No executions match these filters.'}</p><div className="table-scroll" tabIndex={0}><table><caption className="sr-only">Constrained simulation execution ledger</caption><thead><tr><th>Decision</th><th>Security</th><th>Whole shares</th><th>Position / capital</th><th>Capacity limit</th><th>Total costs</th><th>Delisted</th></tr></thead><tbody>{filteredTrades.slice(currentPage*12, (currentPage+1)*12).map(e => <tr key={`${e.decision}-${e.security_id}`}><td>{e.decision}</td><td>{e.security_id}</td><td>{e.shares}</td><td>{percent(e.entry_notional / e.starting_capital)}</td><td>${number(e.capacity_limit)}</td><td>${number(e.entry_cost + e.exit_cost)}</td><td>{e.delisted ? 'Yes' : 'No'}</td></tr>)}</tbody></table></div><div className="pagination"><button className="secondary" disabled={currentPage === 0} onClick={() => setTradePage(currentPage-1)}>Previous executions</button><button className="secondary" disabled={(currentPage+1)*12 >= filteredTrades.length} onClick={() => setTradePage(currentPage+1)}>Next executions</button></div>{!run.portfolio.comparator_runs?.length && <><h3>Same-constraint independent comparators</h3><p>12–1 momentum excludes the most recent 21 sessions; revenue growth uses dated available filings; random ranking is deterministically seeded. Different exclusions remain explicit.</p><div className="table-scroll" tabIndex={0}><table><caption className="sr-only">Constrained baseline comparisons</caption><thead><tr><th>Selector</th><th>Allocation</th><th>Return</th><th>Window-end drawdown</th><th>Executions</th><th>Excluded observations</th></tr></thead><tbody>{run.portfolio.comparators?.map(c => <tr key={c.id ?? c.selector}><td>{c.selector}</td><td>{c.allocation ?? 'Legacy ranked caps'}</td><td>{percent(c.metrics.total_return)}</td><td>{percent(c.metrics.max_drawdown)}</td><td>{c.executions}</td><td>{c.excluded}</td></tr>)}</tbody></table></div></>}<ul>{run.portfolio.limitations.map(l => <li key={l}>{l}</li>)}</ul><a href={`/api/runs/${run.run_id}/reports/portfolio.json`}>Download constrained simulation</a></section>}<section className="panel"><h2>Performance diagnostics</h2><p>FIXTURE calculations. Sparse window returns; annualized Sharpe is unavailable without a daily equity/risk-free series.</p><div className="table-scroll" tabIndex={0}><table><caption className="sr-only">Fixture performance metrics</caption><thead><tr><th>Comparator</th><th>Windows</th><th>Total return</th><th>CAGR</th><th>Window-end drawdown</th><th>Win rate</th><th>Payoff ratio</th></tr></thead><tbody>{Object.entries(v.metrics).map(([key, m]) => <tr key={key}><td>{key}</td><td>{m.windows}</td><td>{percent(m.total_return)}</td><td>{percent(m.cagr)}</td><td>{percent(m.max_drawdown)}</td><td>{percent(m.win_rate)}</td><td>{m.payoff_ratio?.toFixed(2) ?? 'Missing'}</td></tr>)}</tbody></table></div></section>
    <section className="panel"><h2>Chronological split & overlap audit</h2><p>{v.holdout_status}</p><p>Embargo: {v.partitions.embargo_days} calendar days. Purge any earlier outcome ending within the embargo before the next partition starts.</p><div className="scenario-grid">{(['train', 'validation', 'holdout', 'purged'] as const).map(k => <article className="scenario-card" key={k}><h3>{k}</h3><strong>{v.partitions[k].length}</strong><p>{v.partitions[k].join(', ') || 'No windows'}</p></article>)}</div></section>
    <section className="panel"><h2>Cost sensitivity & uncertainty</h2><div className="table-scroll" tabIndex={0}><table><caption className="sr-only">Transaction cost sensitivity</caption><thead><tr><th>Round-trip bps</th><th>Total return</th><th>Window-end drawdown</th></tr></thead><tbody>{v.cost_sensitivity.map(m => <tr key={m.round_trip_bps}><td>{m.round_trip_bps}</td><td>{percent(m.total_return)}</td><td>{percent(m.max_drawdown)}</td></tr>)}</tbody></table></div><p>Paired complete-window bootstrap, {v.paired_window_bootstrap.resamples} resamples. Mean excess versus equal weight: {percent(v.paired_window_bootstrap.mean_excess_versus_equal_weight)}. Illustrative interval: {v.paired_window_bootstrap.interval_95?.map(percent).join(' to ') ?? 'Missing'}.</p><p>These artificial observations cannot support statistical investment claims. No daily-risk or independent holdout inference.</p><a className="text-button" href={`/api/runs/${run.run_id}/reports/validation.json`}>Download validation report</a></section></>;
}

export function Settings({run, preferences, onChange}: {run: Run; preferences: Preferences; onChange: (p: Preferences) => void}) {
  const [policyText, setPolicyText] = useState(JSON.stringify(run.discovery?.policy ?? {}, null, 2));
  const [message, setMessage] = useState('');
  const [riskPolicy, setRiskPolicy] = useState(JSON.stringify(run.portfolio?.policy ?? {}, null, 2));
  const exportPolicy = () => {try {const value: unknown = JSON.parse(policyText); if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(); download('discovery-policy.json', JSON.stringify(value, null, 2), 'application/json'); setMessage('Policy downloaded. The CLI validates all thresholds and weights before a new run.');} catch {setMessage('Enter a valid JSON object before exporting.');}};
  return <><section className="panel"><h2>Watchlist & display preferences</h2><p>Saved locally in this browser. Display filters do not change a materialized research model.</p><div className="input-grid"><label>Minimum displayed 20D dollar volume<input type="number" min="0" value={preferences.minLiquidity} onChange={e => onChange({...preferences, minLiquidity: Math.max(0, Number(e.target.value))})} /></label><label>Minimum displayed factor coverage (fraction)<input type="number" min="0" max="1" step=".05" value={preferences.minCoverage} onChange={e => onChange({...preferences, minCoverage: Math.max(0, Math.min(1, Number(e.target.value)))})} /></label></div><p>{preferences.watchlist.length} saved securities.</p><button className="secondary" onClick={() => onChange({...defaults})}>Reset display preferences</button></section>
    <section className="panel"><h2>Discovery policy & reproducible refresh</h2><p>Model thresholds are frozen into each run. Edit and download a policy, then explicitly build a new local fixture run.</p><label>Discovery policy JSON<textarea aria-label="Discovery policy JSON" className="policy-editor" value={policyText} onChange={e => setPolicyText(e.target.value)} /></label><button className="secondary" onClick={exportPolicy}>Download discovery policy</button><p role="status">{message}</p><code>uv run baghunter demo --policy discovery-policy.json</code><p>Reload local run after the command succeeds. There is no automatic job, provider purchase or deployment.</p><p>Policy digest <span className="hash">{run.discovery?.policy_sha256 ?? 'Unavailable in this archive'}</span></p></section>
    <section className="panel"><h2>Portfolio constraints</h2><p>Whole-share long-only simulation. Policies are validated by the CLI; changing this editor does not rewrite an existing run.</p><label>Portfolio policy JSON<textarea aria-label="Portfolio policy JSON" className="policy-editor" value={riskPolicy} onChange={e => setRiskPolicy(e.target.value)} /></label><button className="secondary" onClick={() => {try {const policy: unknown = JSON.parse(riskPolicy); if (!policy || typeof policy !== 'object' || Array.isArray(policy)) throw new Error(); download('portfolio-policy.json', JSON.stringify(policy, null, 2), 'application/json'); setMessage('Portfolio policy downloaded.');} catch {setMessage('Enter a valid portfolio policy JSON object.');}}}>Download portfolio policy</button><code>uv run baghunter demo --policy discovery-policy.json --portfolio-policy portfolio-policy.json</code></section><section className="panel"><h2>Manual provider imports</h2><p>Run these commands explicitly in a local terminal. They read private .env values; this page never starts downloads or exposes credentials. Use a CIK independently identified from the issuer’s SEC filing, then choose the saved archive in Data Quality or the observation research desk.</p><code>uv run baghunter refresh-finviz --usage-authorized</code><code>uv run baghunter sync-sec --cik YOUR_CIK --include-history</code><p>Imports preserve raw sources. Selecting an issuer does not approve a security/class mapping or historical research coverage.</p></section><section className="panel"><h2>Provider & cache state</h2><p>Research feed: synthetic fixture. Finviz: separately selected saved observations. Historical PIT/delist coverage remains unestablished. SEC: saved verified-source annual/quarterly entity evidence remains separate from security research inputs.</p><p>Run {run.run_id} · model {run.model_version}. Original raw hashes are in Data Quality. Saved runs can be inspected without changing CURRENT.</p><code>uv run baghunter demo</code><code>uv run baghunter audit-history --bundle examples/history-fixture</code><p>Back up data/fixture/latest/runs and the adjacent raw archive together. Recover by selecting a valid archived run in the run selector; activation requires an explicit local pointer change.</p></section></>;
}

export function CohortExplorer({run}: {run: Run}) {
  const [horizon, setHorizon] = useState('1');
  const [anchor, setAnchor] = useState(run.study.cohorts?.anchors[0] ?? run.study.anchor.slice(0, 10));
  const [sector, setSector] = useState('ALL');
  const [threshold, setThreshold] = useState(5);
  const [group, setGroup] = useState('ALL');
  const cohort = run.study.cohorts ? run.study.cohorts.labels.filter(l => l.anchor === anchor && l.horizon_years === Number(horizon) && (sector === 'ALL' || l.sector === sector)) : run.study.labels.filter(l => l.horizon_years === Number(horizon));
  const observed = cohort.filter(l => l.max_multiple !== null);
  const cases = observed.filter(l => l.max_multiple! >= threshold);
  const rows = cohort.filter(l => group === 'ALL' || (group === 'CASE' ? l.max_multiple !== null && l.max_multiple >= threshold : group === 'CONTROL' ? l.max_multiple !== null && l.max_multiple < threshold : l.max_multiple === null));
  return <section className="panel"><div className="panel-title"><div><h2>Cohort explorer</h2><p>Closed artificial universe. Complete and missing outcomes remain in the denominator; this is not a population base-rate estimate.</p></div><a href={`/api/runs/${run.run_id}/reports/historical_cohorts.csv`}>Export cohort CSV</a><a href={`/api/runs/${run.run_id}/reports/cohort_grid.json`}>Download all cohort diagnostics</a></div><div className="filters"><label>Cohort anchor<select value={anchor} onChange={e => setAnchor(e.target.value)}>{(run.study.cohorts?.anchors ?? [run.study.anchor.slice(0, 10)]).map(a => <option key={a}>{a}</option>)}</select></label><label>Cohort sector<select value={sector} onChange={e => setSector(e.target.value)}><option value="ALL">All sectors</option>{[...new Set(run.study.cohorts?.labels.map(l => l.sector))].map(s => <option key={s}>{s}</option>)}</select></label><label>Outcome horizon<select value={horizon} onChange={e => setHorizon(e.target.value)}>{[1, 2, 3, 5].map(y => <option key={y} value={y}>{y} years</option>)}</select></label><label>Maximum-hit threshold<select value={threshold} onChange={e => setThreshold(Number(e.target.value))}>{[5, 10, 20, 100].map(x => <option key={x} value={x}>{x}×</option>)}</select></label><label>Outcome group<select value={group} onChange={e => setGroup(e.target.value)}><option value="ALL">All outcomes</option><option value="CASE">Cases</option><option value="CONTROL">Noncases</option><option value="MISSING">Missing horizons</option></select></label></div><p>{cases.length} cases / {observed.length} observed / {cohort.length} eligible; {cohort.length - observed.length} missing. Observed fixture fraction: {observed.length ? percent(cases.length / observed.length) : 'Missing'}.</p><ul>{rows.map(l => <li key={l.security_id}>{l.security_id}: {l.max_multiple === null ? 'Missing horizon' : `${l.max_multiple.toFixed(2)}× maximum`} · terminal {percent(l.terminal_total_return)} · {l.coverage_flag}</li>)}</ul>{!rows.length && <p>No outcomes match this selection.</p>}</section>;
}

export function RunTools({run, onSelect}: {run: Run; onSelect: (id: string) => void}) {
  const [runs, setRuns] = useState<{run_id: string; asof: string}[]>([]);
  const [error, setError] = useState('');
  const comparisonRequest = useRef<AbortController | null>(null);
  useEffect(() => () => comparisonRequest.current?.abort(), []);
  const [comparison, setComparison] = useState<{previous_id: string; asof?: string; previous_asof?: string; policy_changed: boolean | null; changes: {security_id: string; change: string; before_stage: string | null; after_stage: string | null; score_change: number | null}[]} | null>(null);
  useEffect(() => {const controller = new AbortController(); fetch('/api/runs', {signal: controller.signal}).then(async r => {if (!r.ok) throw new Error('Saved run index unavailable.'); return r.json();}).then(setRuns).catch((e: Error) => {if (e.name !== 'AbortError') setError(e.message);}); return () => controller.abort();}, [run.run_id]);
  const compare = async (id: string) => {
    comparisonRequest.current?.abort();
    const controller = new AbortController(); comparisonRequest.current = controller;
    setComparison(null); setError(''); if (!id) return;
    try {
      const r = await fetch(`/api/runs/${run.run_id}/compare/${id}`, {signal: controller.signal});
      if (!r.ok) throw new Error('Run comparison unavailable.');
      const data = await r.json() as NonNullable<typeof comparison> & {run_id: string; previous_id: string};
      if (data.run_id !== run.run_id || data.previous_id !== id) throw new Error('Comparison response belongs to a different run selection.');
      if (data.asof !== undefined && data.asof !== run.asof) throw new Error('Comparison clock does not match the selected run.');
      if (!controller.signal.aborted) setComparison(data);
    } catch (e) {if (!controller.signal.aborted) setError((e as Error).message);}
  };
  return <section className="panel"><div className="filters"><label>Inspect saved run<select value={run.run_id} onChange={e => onSelect(e.target.value)}>{runs.map(r => <option key={r.run_id} value={r.run_id}>{r.asof} · {r.run_id}</option>)}</select></label><label>Compare against saved run<select defaultValue="" key={run.run_id} onChange={e => void compare(e.target.value)}><option value="">Choose comparison</option>{runs.filter(r => r.run_id !== run.run_id).map(r => <option key={r.run_id} value={r.run_id}>{r.asof} · {r.run_id}</option>)}</select></label><a href={`/api/runs/${run.run_id}/reports/baghunter_watchlist.csv`}>Download watchlist CSV</a></div>{error && <p role="alert">{error}</p>}{comparison && <><h2>Changes since comparison run</h2>{comparison.asof === run.asof && comparison.previous_asof && Number.isFinite(Date.parse(comparison.previous_asof)) && Date.parse(comparison.previous_asof)<Date.parse(run.asof) ? <a href={`/api/runs/${run.run_id}/reports/discovery_digest.md?previous=${comparison.previous_id}`}>Download interval discovery digest</a> : <p>An interval digest requires a verified earlier comparison clock. Same-clock policy comparisons do not imply a refresh interval.</p>}<p>{comparison.policy_changed === null ? 'Policy comparison unavailable: an archived fingerprint is missing.' : comparison.policy_changed ? 'Policy changed: score differences combine model and observation changes.' : 'Same discovery policy.'}</p><ul>{comparison.changes.map(c => <li key={c.security_id}>{c.security_id}: {c.change} · {c.before_stage ?? 'Absent'} → {c.after_stage ?? 'Absent'} · score Δ {c.score_change?.toFixed(2) ?? 'Missing'}</li>)}</ul></>}</section>;
}
