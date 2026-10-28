import { useState } from 'react';

export type Sensitivity = {status: string; limitations: string[]; variants: {name: string; ablated_component?: string | null; weights: Record<string, number>; min_dollar_volume: number; excluded: number; ranked: {security_id: string; rank: number; score: number; factor_coverage: number; rank_change: number | null}[]}[]};

export function RankingSensitivity({data, runId}: {data?: Sensitivity; runId: string}) {
  const [variant, setVariant] = useState('frozen_policy');
  const current = data?.variants.find(v => v.name === variant) ?? data?.variants[0];
  if (!data || !current) return <section className="panel"><h2>Ranking sensitivity unavailable</h2><p>Rebuild this archive to materialize the dated-factor diagnostics.</p></section>;
  return <section className="panel"><p className="eyebrow">FROZEN AS-OF FACTORS · FIXTURE</p><h2>Weight & liquidity sensitivity</h2><p>Compare explicit weight variants, stricter liquidity floors and leave-one-family-out ablations using the same dated factors. This does not measure returns or select a winning policy.</p>
    <label>Ranking sensitivity variant<select aria-label="Ranking sensitivity variant" value={current.name} onChange={e => setVariant(e.target.value)}>{data.variants.map(v => <option key={v.name}>{v.name}</option>)}</select></label>
    <p>Removed family: {current.ablated_component?.replaceAll("_", " ") ?? "None"}. Remaining factors keep their declared weights; missing weight is not redistributed.</p><p>Minimum known 20-session dollar volume: ${current.min_dollar_volume.toLocaleString('en-US')}. Excluded: {current.excluded}. Price floor and security eligibility remain frozen.</p>
    <div className="table-scroll" tabIndex={0}><table><caption className="sr-only">As-of ranking sensitivity comparison</caption><thead><tr><th>Rank</th><th>Permanent ID</th><th>Weighted score</th><th>Covered weight</th><th>Rank change versus frozen policy</th></tr></thead><tbody>{current.ranked.map(r => <tr key={r.security_id}><td>{r.rank}</td><td>{r.security_id}</td><td>{r.score.toFixed(2)}</td><td>{(r.factor_coverage*100).toFixed(1)}%</td><td>{r.rank_change === null ? 'Outside original universe' : r.rank_change}</td></tr>)}</tbody></table></div>
    {!current.ranked.length && <p>No securities satisfy this variant.</p>}
    <details><summary>Exact variant weights and interpretation</summary><pre>{JSON.stringify(current.weights, null, 2)}</pre><ul>{data.limitations.map(l => <li key={l}>{l}</li>)}</ul></details><a href={`/api/runs/${runId}/reports/discovery_sensitivity.json`}>Download ranking sensitivity</a>
  </section>;
}
