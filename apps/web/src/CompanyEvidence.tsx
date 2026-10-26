import {useEffect, useState} from 'react';
import {SecFinancialProfile, type FinancialProfile} from './SecFinancialProfile';
import {SecStatements} from './SecStatements';

export type CompanyEvidence = {bundle_id: string; issuer?: {name: string | null; tickers: string[] | null; exchanges: string[] | null; scope: string; source_sha256: string; retrieved_at: string}; manifest: {security_id: string; cik: string; asof: string; lag_hours: number; submissions: {url: string; sha256: string; retrieved_at: string}; companyfacts: {url: string; sha256: string; retrieved_at: string}}; financial_profile: FinancialProfile};

export function CompanyEvidencePicker({bundleId, onSelect, onVerified, onUseRevenue}: {bundleId: string; onSelect: (id: string) => void; onVerified: (data: CompanyEvidence | null) => void; onUseRevenue: (value: number) => void}) {
  const [entries, setEntries] = useState<{bundle_id: string; cik: string; asof: string}[]>([]);
  const [indexError, setIndexError] = useState('');
  const [indexLoaded, setIndexLoaded] = useState(false);
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState<{key: string; data: CompanyEvidence} | null>(null);
  const [failure, setFailure] = useState<{key: string; error: string} | null>(null);
  const key = JSON.stringify([bundleId, revision]);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/sec/bundles', {signal: controller.signal}).then(async response => {
      if (!response.ok) throw new Error('Saved SEC issuer index unavailable.');
      const body = await response.json() as {bundles: typeof entries};
      if (!Array.isArray(body.bundles)) throw new Error('Invalid saved SEC issuer index.');
      if (!controller.signal.aborted) {setEntries(body.bundles); setIndexError(''); setIndexLoaded(true);}
    }).catch((error: Error) => {if (!controller.signal.aborted) setIndexError(error.message);});
    return () => controller.abort();
  }, [revision]);
  useEffect(() => {
    onVerified(null);
    if (!bundleId) return;
    const controller = new AbortController();
    fetch(`/api/sec/bundles/${bundleId}?limit=1`, {signal: controller.signal}).then(async response => {
      if (!response.ok) throw new Error('Selected SEC issuer evidence failed verification. Clear or reload the attachment.');
      const data = await response.json() as CompanyEvidence;
      if (data.bundle_id !== bundleId || !data.financial_profile || data.financial_profile.asof !== data.manifest.asof || data.financial_profile.security_id !== data.manifest.security_id || data.manifest.security_id !== `sec-cik-${data.manifest.cik}-unverified`) throw new Error('Issuer evidence does not match the selected archive and clock.');
      if (!controller.signal.aborted) {const selected = {bundle_id:data.bundle_id, issuer:data.issuer, manifest:data.manifest, financial_profile:data.financial_profile}; setResult({key, data:selected}); onVerified(selected);}
    }).catch((error: Error) => {if (!controller.signal.aborted) {setFailure({key, error: error.message}); onVerified(null);}});
    return () => controller.abort();
  }, [bundleId, key, onVerified]);
  const data = result?.key === key ? result.data : null;
  const error = failure?.key === key ? failure.error : null;
  return <section className="panel company-evidence" aria-label="Selected SEC issuer evidence"><h3>SEC evidence for this research draft</h3><p>Choose an archived filer explicitly. This selection is your research association; it does not verify the Finviz security, share class or historical identity. No issuer is matched automatically.</p>
    <label>Attach saved SEC issuer evidence<select aria-label="Attach saved SEC issuer evidence" value={bundleId} onChange={event => onSelect(event.target.value)}><option value="">No SEC evidence attached</option>{entries.map(entry => <option key={entry.bundle_id} value={entry.bundle_id}>CIK {entry.cik} · {entry.asof} · {entry.bundle_id.slice(0,12)}</option>)}{bundleId && !entries.some(entry => entry.bundle_id === bundleId) && <option value={bundleId}>Saved selection · {bundleId.slice(0,12)} · index unavailable</option>}</select></label><button className="secondary" onClick={() => {onVerified(null); setRevision(value => value+1);}}>Reload issuer evidence</button>
    {indexError && <p role="alert">{indexError}</p>}{error ? <p role="alert">{error}</p> : bundleId && !data ? <p role="status">Verifying attached issuer evidence…</p> : data && <>
      <p>Selected SEC filer: {data.issuer?.name ?? 'Name unavailable'} · CIK {data.manifest.cik}. Current reported tickers: {data.issuer?.tickers == null ? 'Unavailable' : data.issuer.tickers.length ? data.issuer.tickers.join(', ') : 'None reported'}. Current issuer metadata was retrieved {data.issuer?.retrieved_at ?? data.manifest.submissions.retrieved_at}; it is not a historical security assignment.</p><p>Financial evidence clock {data.manifest.asof}; original submissions SHA-256 <span className="hash">{data.manifest.submissions.sha256}</span>. Original extraction vintages remain uncertified.</p>
      {data.financial_profile.latest?.revenue != null && <button className="secondary" onClick={() => onUseRevenue(data.financial_profile.latest!.revenue!)}>Use selected SEC annual revenue as an assumption</button>}
      <details><summary>Inspect attached annual financial evidence</summary><SecFinancialProfile profile={data.financial_profile} cik={data.manifest.cik} bundleId={bundleId}/></details><SecStatements bundleId={bundleId}/>
    </>}
    {indexLoaded && !entries.length && !indexError && <><p>No SEC archives are listed. Run the manual import in your local terminal using a CIK independently identified from the issuer's SEC filing, then reload issuer evidence. The command reads private .env settings; the browser does not download provider data.</p><code>uv run baghunter sync-sec --cik YOUR_CIK --include-history</code></>}
  </section>;
}
