import type { Run } from './main';
const percent = (v: number | null | undefined) => v == null ? 'Missing' : `${(v * 100).toFixed(2)}%`;

export type DailyRisk = {max_drawdown_recovery_sessions?: number | null; drawdown_recovery_status?: string; underwater_sessions_at_end?: number; return_observations?: number; status: string; observations: number; period_start: string; period_end: string;
  total_return: number; cagr: number | null; max_drawdown: number; maximum_underwater_sessions: number;
  annualized_volatility: number | null; sharpe_zero_risk_free: number | null; sortino_zero_target: number | null;
  worst_daily_return: number | null; daily_tail_5pct: number | null; skewness: number | null;
  ratio_status: string; assumptions: string[]};

export function DailyRiskPanel({run}: {run: Run}) {
  const risk = run.portfolio?.daily_risk;
  const curve = run.portfolio?.daily_curve ?? [];
  if (!risk || !curve.length) return <section className="panel"><h2>Daily portfolio risk unavailable</h2><p>This archive contains window-end diagnostics only. Rebuild to materialize daily marks; window endpoints cannot reveal every loss during a holding period.</p></section>;
  const initial = curve[0].equity;
  const values = curve.map(p => p.equity / initial);
  const min = Math.min(...values), max = Math.max(...values);
  return <section className="panel"><p className="eyebrow">DAILY CLOSES + CASH + COSTS · FIXTURE</p><h2>Daily marked portfolio risk</h2><p>{risk.period_start} → {risk.period_end} · {risk.observations} marked sessions. This includes losses between window exits. Intraday drawdown is not observed.</p>
    <div className="scenario-grid">{[
      ['Daily-close maximum drawdown', percent(risk.max_drawdown)], ['Annualized daily volatility', percent(risk.annualized_volatility)],
      ['Sharpe · zero risk-free', risk.sharpe_zero_risk_free?.toFixed(2) ?? 'Undefined'], ['Sortino · zero target', risk.sortino_zero_target?.toFixed(2) ?? 'Undefined'],
      ['Observed 5th-percentile daily return', percent(risk.daily_tail_5pct)], ['Daily return skewness', risk.skewness?.toFixed(2) ?? 'Undefined'], ['Worst-drawdown recovery', risk.max_drawdown_recovery_sessions == null ? 'Not observed' : `${risk.max_drawdown_recovery_sessions} sessions`], ['Worst close-to-close return', percent(risk.worst_daily_return)], ['Longest underwater stretch', `${risk.maximum_underwater_sessions} sessions`],
    ].map(([label, value]) => <article className="scenario-card" key={label}><h3>{label}</h3><strong>{value}</strong></article>)}</div>
    <figure className="chart"><svg viewBox="0 0 810 245" role="img" aria-label="Daily marked fixture portfolio equity per initial dollar including cash gaps">
      {[0, 1, 2, 3].map(i => <g key={i}><line x1="55" x2="790" y1={20+i*55} y2={20+i*55} stroke="#33434d" strokeDasharray="3 5"/><text x="0" y={25+i*55} fill="#b8cbd4" fontSize="12">{(max-(max-min)*i/3).toFixed(2)}</text></g>)}
      <polyline fill="none" stroke="#75e4cd" strokeWidth="2.5" points={values.map((v, i) => `${55+i/Math.max(1, values.length-1)*735},${190-(v-min)/(max-min || 1)*170}`).join(' ')}/>
      <text x="55" y="235" fill="#b8cbd4" fontSize="11">{risk.period_start}</text><text x="670" y="235" fill="#b8cbd4" fontSize="11">{risk.period_end}</text>
    </svg><figcaption>Wealth per initial dollar · daily closes, distributions and cash · fixture weekday calendar. No empirical performance claim.</figcaption></figure>
    <p>Recovery status: {risk.drawdown_recovery_status?.replaceAll("_", " ").toLowerCase() ?? "Unavailable in this archive"}. Recovery remains unobserved if the prior peak was not regained. {risk.return_observations == null ? "" : `${risk.return_observations} defined daily returns.`}</p><p>Ratio status: {risk.ratio_status}. Zero-variance or exhausted equity does not receive an invented risk ratio.</p><ul>{risk.assumptions.map(a => <li key={a}>{a}</li>)}</ul><a href={`/api/runs/${run.run_id}/reports/portfolio.json`}>Download daily equity and risk report</a>
  </section>;
}
