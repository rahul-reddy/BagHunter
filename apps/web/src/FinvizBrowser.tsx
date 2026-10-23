import { useEffect, useState } from 'react';

type Observation = {
  ticker: string; company: string; sector: string | null; industry: string | null;
  country: string | null; market_cap_reported: string | null; price_reported: string | null;
  pe_reported: string | null; change_percent_reported: string | null; volume_shares: string | null;
  security_id: null; security_type: 'unknown';
};
type SnapshotPage = {
  coverage: { snapshot_id: string; source_sha256: string; mode: string; retrieved_at: string;
    ingested_at: string; rows: number; missing: Record<string, number>; zero_pe_reported: number;
    flags: string[]; status: string; provider_observation_time: null };
  age_hours: number; stale: boolean; total: number; offset: number; limit: number;
  observations: Observation[];
};
const reported = (value: string | number | null) => value === null ? 'Missing' : String(value);

export function FinvizBrowser() {
  const [input, setInput] = useState('');
  const [request, setRequest] = useState({ q: '', offset: 0, revision: 0 });
  const [result, setResult] = useState<{ key: string; data: SnapshotPage } | null>(null);
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null);
  const key = JSON.stringify(request);
  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({ q: request.q, offset: String(request.offset), limit: '50' });
    fetch(`/api/finviz/observations?${params}`, { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('Select a valid local Finviz snapshot using the setup guide.');
      return response.json() as Promise<SnapshotPage>;
    }).then(data => {
      if (!controller.signal.aborted) setResult({ key, data });
    }).catch((error: Error) => {
      if (!controller.signal.aborted && error.name !== 'AbortError') setFailure({ key, message: error.message });
    });
    return () => controller.abort();
  }, [key, request.q, request.offset]);
  const data = result?.key === key ? result.data : null;
  const error = failure?.key === key ? failure.message : null;
  return <>
    <div className="warning" role="note"><strong>FINVIZ · SAVED OBSERVATIONS · RESEARCH ONLY</strong>
      <span>Not a live feed or candidate ranking. Security types and permanent identities remain unresolved.</span></div>
    <section className="panel"><h2>Snapshot explorer</h2>
      <p>Search reported ticker, company, sector or industry. Alphabetical order; no screening scores.</p>
      <form className="filters" onSubmit={event => {
        event.preventDefault(); setRequest(previous => ({ q: input.trim(), offset: 0, revision: previous.revision + 1 }));
      }}><label>Search Finviz observations<input value={input} maxLength={100} onChange={event => setInput(event.target.value)}
        placeholder="Ticker, company, sector or industry" /></label><button className="secondary" type="submit">Search observations</button>
        <button className="secondary" type="button" onClick={() => setRequest(previous => ({ ...previous, revision: previous.revision + 1 }))}>Reload snapshot</button></form>
      {error ? <div role="alert"><h3>Finviz snapshot unavailable</h3><p>{error}</p>
        <p>Local setup: docs/FINVIZ.md. Existing fixture research remains in its own views.</p></div>
        : !data ? <p role="status">Loading selected snapshot…</p> : <>
          <p className="tag">{data.coverage.mode === 'FIXTURE' ? 'SYNTHETIC FINVIZ TEST FIXTURE' : 'EXTERNAL · UNVERIFIED'}</p>
          <div className="asof"><span>Retrieved: {data.coverage.retrieved_at}</span>
            <span>{data.stale ? 'STALE SNAPSHOT' : 'SAVED SNAPSHOT'} · {data.age_hours.toFixed(1)} hours since retrieval</span></div>
          <p>Provider observation time: unknown. Retrieval time does not establish quote freshness.</p>
          <p>Market cap: reported scale, unverified. Price: reported currency/adjustments unverified.
            Volume: shares in current/last session. Change: reported percentage, not a backtest return.</p>
          <p role="status">{data.total === 0 ? 'No observations match this search.' :
            `Showing ${data.offset + 1}–${Math.min(data.offset + data.limit, data.total)} of ${data.total} observations`}</p>
          <div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable Finviz observations"><table><caption className="sr-only">Saved Finviz observations with unresolved identities</caption>
            <thead><tr>{['Ticker / company', 'Sector / industry', 'Market cap (reported scale)', 'Price (reported)', 'P/E (reported)', 'Change (%)', 'Volume (shares)', 'Identity / type'].map(title => <th key={title}>{title}</th>)}</tr></thead>
            <tbody>{data.observations.map(row => <tr key={row.ticker}>
              <td>{row.ticker}<small className="observation-name">{row.company}</small></td>
              <td>{reported(row.sector)}<small className="observation-name">{reported(row.industry)}</small></td>
              <td>{reported(row.market_cap_reported)}</td><td>{reported(row.price_reported)}</td>
              <td>{row.pe_reported !== null && Number(row.pe_reported) === 0 ? '0 (reported; unresolved)' : reported(row.pe_reported)}</td>
              <td>{row.change_percent_reported === null ? 'Missing' : `${row.change_percent_reported}%`}</td>
              <td>{reported(row.volume_shares)}</td><td>Unresolved / unknown</td>
            </tr>)}</tbody></table></div>
          <div className="pagination"><button className="secondary" disabled={data.offset === 0}
            onClick={() => setRequest(previous => ({ ...previous, offset: Math.max(0, previous.offset - data.limit) }))}>Previous observations</button>
            <button className="secondary" disabled={data.offset + data.limit >= data.total}
              onClick={() => setRequest(previous => ({ ...previous, offset: previous.offset + data.limit }))}>Next observations</button></div>
          <details><summary>Source lineage and coverage gaps</summary>
            <p>Snapshot <span className="hash">{data.coverage.snapshot_id}</span></p>
            <p>CSV SHA-256 <span className="hash">{data.coverage.source_sha256}</span></p>
            <p>Ingested: {data.coverage.ingested_at}. Source rows: {data.coverage.rows}.</p>
            <p>Missing market cap: {data.coverage.missing.market_cap_reported}; missing price: {data.coverage.missing.price_reported};
              missing change: {data.coverage.missing.change_fraction}; reported zero P/E: {data.coverage.zero_pe_reported}.</p>
            <ul>{data.coverage.flags.map(flag => <li key={flag}>{flag.replaceAll('_', ' ')}</li>)}</ul>
            <p>These observations do not supply archived membership, original filing vintages or delisting proceeds.</p>
          </details>
        </>}
    </section>
  </>;
}
