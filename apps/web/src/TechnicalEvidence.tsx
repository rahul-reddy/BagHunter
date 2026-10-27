export type Technical = {
  policy?: string; asof_time?: string; observations?: number; source_ids?: string[];
  latest_available_at?: string; adjustment_basis?: string; missing?: {field: string; reason: string}[];
  sma_20: number | null; sma_50: number | null; sma_200: number | null;
  high_20_prior: number | null; high_120_prior: number | null;
  atr_20: number | null; stale_calendar_days: number | null;
  ema_8?: number | null; ema_21?: number | null; high_60_prior?: number | null;
  distance_high_20?: number | null; distance_high_60?: number | null; distance_high_120?: number | null;
  breakout_20?: boolean | null; breakout_60?: boolean | null; breakout_120?: boolean | null;
  volatility_20d?: number | null; volatility_60d?: number | null; volatility_contraction?: number | null;
  gap_open?: number | null; mean_absolute_gap_20d?: number | null;
  base_duration_windows?: number | null; base_left_censored?: boolean | null;
  base_window?: number; base_cap?: number; base_width_limit?: number;
};
export type RelativeEvidence = {
  policy: string; scope: string; universe_count: number; sector_count: number;
  rank_percentile_63d: number | null; sector_rank_percentile_63d: number | null;
  sector_relative_63d: number | null; sector_participation_21d: number | null;
  sector_dispersion_63d: number | null; universe_dispersion_63d: number | null;
};
const number = (value: number | null | undefined) => value == null ? 'Missing' : value.toFixed(3);
const percent = (value: number | null | undefined) => value == null ? 'Missing' : `${(value * 100).toFixed(2)}%`;

export function TechnicalEvidence({technical: t, relative: r, runId}: {technical?: Technical; relative?: RelativeEvidence; runId: string}) {
  return <section className="panel technical-evidence" aria-label="Technical evidence">
    <h2>Dated technical evidence</h2>
    {!t?.policy ? <p>Technical catalog unavailable in this archive. Refresh the fixture pipeline to create a new version; saved history stays unchanged.</p> : <>
      <p>{t.policy} · {t.observations} available observations · {t.adjustment_basis} prices · clock {t.asof_time}. Descriptive diagnostics; scoring and stage thresholds retain their existing policy.</p>
      <div className="table-scroll" tabIndex={0}><table><caption>Distance from prior highs</caption><thead><tr><th>Prior observations</th><th>High</th><th>Close / high − 1</th><th>Strict breakout</th></tr></thead><tbody>{([20, 60, 120] as const).map(w => <tr key={w}><td>{w}</td><td>{number(t[`high_${w}_prior`])}</td><td>{percent(t[`distance_high_${w}`])}</td><td>{t[`breakout_${w}`] == null ? 'Missing' : t[`breakout_${w}`] ? 'Yes' : 'No'}</td></tr>)}</tbody></table></div>
      <dl className="metrics">
        <div><dt>20D / 60D annualized volatility</dt><dd>{percent(t.volatility_20d)} / {percent(t.volatility_60d)}</dd></div>
        <div><dt>Volatility contraction (20D / 60D)</dt><dd>{number(t.volatility_contraction)}</dd></div>
        <div><dt>Latest opening gap / mean absolute 20D gap</dt><dd>{percent(t.gap_open)} / {percent(t.mean_absolute_gap_20d)}</dd></div>
        <div><dt>Consecutive prior base windows</dt><dd>{t.base_duration_windows == null ? 'Missing' : `${t.base_duration_windows}${t.base_left_censored ? ' or more (history/cap boundary)' : ''}`}</dd></div>
        <div><dt>EMA8 / EMA21</dt><dd>{number(t.ema_8)} / {number(t.ema_21)}</dd></div>
      </dl>
      <details><summary>Formulas, missingness and source clocks</summary><p>Daily simple close returns; population standard deviation over 20/60 returns × √252. Contraction divides short by long volatility; a zero reference is missing. Gap = open / previous available close − 1. Prior highs exclude the current observation.</p><p>Base duration counts consecutive prior {t.base_window}-observation rolling windows whose high / low − 1 is at most {percent(t.base_width_limit)}, stopping at the first wider window, available history or {t.base_cap} windows. An uninterrupted run is a lower bound. These are observation counts, not elapsed trading days. EMA starts at the first available close. Raw prices can contain corporate-action effects.</p><p>Latest included price publication: {t.latest_available_at}. Sources: {t.source_ids?.join(', ') || 'Missing'}. Missing fields: {(t.missing ?? []).map(({field, reason}) => `${field}: ${reason.replaceAll('_', ' ')}`).join('; ') || 'None'}.</p></details>
    </>}
    {r ? <><h3>Cross-section and sector proxy</h3><p>63D market rank: {percent(r.rank_percentile_63d)} ({r.universe_count} names); sector rank: {percent(r.sector_rank_percentile_63d)} ({r.sector_count} names). Sector-relative 63D return: {percent(r.sector_relative_63d)}. Positive 21D sector participation: {percent(r.sector_participation_21d)}. 63D sector / universe dispersion: {percent(r.sector_dispersion_63d)} / {percent(r.universe_dispersion_63d)}.</p><p>Ranks use average ties scaled from 0 to 1. Universe: known common equities with sufficient history before price/liquidity filters. Sector-relative return subtracts the other sector members’ mean; participation includes the subject. Single-member ranks/dispersion are missing. Sector is a proxy; dated industry membership is unavailable.</p></> : <p>Cross-section evidence unavailable in this archive.</p>}
    <a href={`/api/runs/${runId}/reports/technical_evidence.json`}>Download dated technical evidence</a>
  </section>;
}
