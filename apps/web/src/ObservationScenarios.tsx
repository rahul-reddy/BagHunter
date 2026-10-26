import {useEffect, useRef, useState} from 'react';
import {parseAssumptions, type AssumptionStrings, type CompanyScenario} from './observationResearch';

const labels: Record<keyof AssumptionStrings, string> = {revenue: 'Research starting revenue (USD assumption)', shares: 'Research starting shares (assumption)', net_debt: 'Research net debt (USD assumption)', reference_price: 'Research reference price (USD assumption)', years: 'Research scenario horizon (years)', dilution: 'Research annual dilution (fraction)', growth: 'Research annual revenue growth (fraction)', margin: 'Research operating margin (fraction)', multiple: 'Research EV / operating earnings multiple'};

export function ObservationScenarios({inputs, onInputs, contextKey, enabled, onCalculated, results}: {inputs: AssumptionStrings; onInputs: (inputs: AssumptionStrings) => void; contextKey: string; enabled: boolean; onCalculated: (key: string, scenarios: CompanyScenario[]) => void; results: CompanyScenario[] | null}) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const request = useRef<AbortController | null>(null);
  const key = JSON.stringify([contextKey, inputs]);
  useEffect(() => {request.current?.abort(); setBusy(false); setError(''); return () => request.current?.abort();}, [key]);
  const calculate = async () => {
    const values = parseAssumptions(inputs);
    if (!values || !enabled) {setError('Enter every assumption explicitly and verify the selected evidence before calculating.'); return;}
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setBusy(true); setError('');
    onCalculated(key, []);
    const variants = [{name: 'Bear', assumptions: {...values, growth: values.growth-.1, margin: values.margin-.05, multiple: Math.max(0, values.multiple-5)}}, {name: 'Base', assumptions: values}, {name: 'Bull', assumptions: {...values, growth: values.growth+.1, margin: values.margin+.05, multiple: values.multiple+5}}];
    try {
      const scenarios = await Promise.all(variants.map(async variant => {
        const query = new URLSearchParams(Object.entries(variant.assumptions).map(([name, value]) => [name, String(value)]));
        const response = await fetch(`/api/scenario?${query}`, {signal: controller.signal});
        if (!response.ok) throw new Error('One or more scenario assumptions exceed supported bounds. Check all three displayed case adjustments.');
        return {...variant, value: await response.json() as CompanyScenario['value']};
      }));
      if (!controller.signal.aborted) onCalculated(key, scenarios);
    } catch (problem) {if (!controller.signal.aborted) setError((problem as Error).message);}
    finally {if (!controller.signal.aborted) setBusy(false);}
  };
  return <section className="panel" aria-label="Observation assumption scenarios"><h3>Assumption scenarios for this research draft</h3><p>Enter every financial input explicitly. Finviz reported price/market-cap values and SEC weighted shares are not converted or inserted automatically. Optional SEC revenue copying remains your assumption about the selected filer.</p>
    <div className="input-grid">{(Object.keys(labels) as (keyof AssumptionStrings)[]).map(name => <label key={name}>{labels[name]}<input aria-label={labels[name]} type="number" step={name === 'years' ? '1' : 'any'} value={inputs[name]} onChange={event => onInputs({...inputs, [name]: event.target.value})}/></label>)}</div>
    <p>Bear: growth −10 percentage points, margin −5 points and multiple −5 (minimum zero). Base: entered assumptions. Bull: growth +10 points, margin +5 points and multiple +5. Revenue, reference price, shares, dilution, horizon and net debt are shared. Unsupported cases fail explicitly.</p>
    <button className="secondary" disabled={busy || !enabled || !parseAssumptions(inputs)} onClick={() => void calculate()}>Calculate research scenarios</button>
    {!enabled && <p>Wait for the selected issuer evidence to verify, or clear the attachment to model assumptions alone.</p>}{busy && <p role="status">Calculating assumption scenarios…</p>}{error && <p role="alert">{error}</p>}
    {results ? <div className="scenario-grid">{results.map(scenario => <article className="scenario-card" key={scenario.name}><h4>{scenario.name} assumption case</h4><strong>{new Intl.NumberFormat('en-US', {style:'currency',currency:'USD',maximumFractionDigits:2}).format(scenario.value.per_share_value)}</strong><p>Modeled per-share value; not a target or forecast. Diluted shares {scenario.value.diluted_shares.toLocaleString('en-US')}.</p><details><summary>{scenario.name} exact assumptions</summary><pre>{JSON.stringify(scenario.assumptions,null,2)}</pre></details></article>)}</div> : <p>No current scenario calculation. Editing inputs, loading a draft or changing evidence clears prior results.</p>}
    <p>EV operating-earnings arithmetic subtracts assumed net debt once and floors equity at zero. No probabilities, discount rate, financing, tax or dividend model; class identity and USD applicability are unverified.</p>
  </section>;
}
