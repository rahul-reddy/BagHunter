import { useEffect, useState } from 'react';
import { download } from './downloads';

type EventStatus = 'PLANNED' | 'OBSERVED' | 'INVALIDATED';
export type Catalyst = {id: string; date: string; title: string; source: string; condition: string; status: EventStatus};
const validDate = (value: string) => /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
const validSource = (value: string) => {if (!value) return true; try {const url = new URL(value); return url.protocol === 'https:' && !url.username && !url.password;} catch {return false;}};
const validEvent = (e: Catalyst) => e && typeof e.id === 'string' && e.id.length <= 100 && typeof e.date === 'string' && validDate(e.date) && typeof e.title === 'string' && e.title.length > 0 && e.title.length <= 300 && typeof e.source === 'string' && e.source.length <= 2048 && validSource(e.source) && typeof e.condition === 'string' && e.condition.length <= 1000 && ['PLANNED', 'OBSERVED', 'INVALIDATED'].includes(e.status);

export function CatalystCalendar({securityId, ticker, onChange}: {securityId: string; ticker: string; onChange?: (events:Catalyst[]) => void}) {
  const key = `baghunter.catalysts.v1.${securityId}`;
  const [events, setEvents] = useState<Catalyst[]>(() => {try {const data: unknown = JSON.parse(localStorage.getItem(key) ?? '[]'); return Array.isArray(data) && data.length <= 100 && data.every(validEvent) ? data : [];} catch {return [];}});
  useEffect(() => {onChange?.(events);}, [events,onChange]);
  const [date, setDate] = useState('');
  const [title, setTitle] = useState('');
  const [source, setSource] = useState('');
  const [condition, setCondition] = useState('');
  const [filter, setFilter] = useState('ALL');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const persist = (next: Catalyst[]) => {onChange?.(next); setEvents(next); try {localStorage.setItem(key, JSON.stringify(next)); setMessage('Calendar saved in this browser.');} catch {setMessage('Browser storage unavailable; export the calendar to preserve it.');}};
  const ordered = [...events].sort((a, b) => a.date.localeCompare(b.date) || a.title.localeCompare(b.title));
  return <section className="panel"><div className="panel-title"><div><h2>Catalyst calendar</h2><p>{ticker} · dated operator assertions. Planned, observed and invalidated statuses are not independent evidence verification.</p></div><button className="secondary" onClick={() => download(`FIXTURE-${securityId}-catalysts.json`, JSON.stringify({mode: 'FIXTURE_USER_ASSERTIONS', security_id: securityId, events: ordered}, null, 2), 'application/json')}>Export catalyst calendar</button></div>
    <form onSubmit={event => {event.preventDefault(); setError(''); if (!validDate(date) || !title.trim() || !validSource(source)) {setError('Enter a valid date, catalyst title and optional public HTTPS source without embedded credentials.'); return;} if (events.length >= 100) {setError('Calendar limit reached: export or remove an event before adding another.'); return;} persist([...events, {id: crypto.randomUUID(), date, title: title.trim(), source, condition, status: 'PLANNED'}]); setTitle(''); setSource(''); setCondition('');}}>
      <div className="input-grid"><label>Catalyst date<input type="date" value={date} onChange={e => setDate(e.target.value)} /></label><label>Catalyst title<input value={title} maxLength={300} onChange={e => setTitle(e.target.value)} /></label><label>Catalyst source URL<input type="text" value={source} maxLength={2048} onChange={e => setSource(e.target.value)} placeholder="https://issuer.example/report" /></label><label>Event falsification condition<input value={condition} maxLength={1000} onChange={e => setCondition(e.target.value)} /></label></div><button className="secondary" type="submit">Add catalyst event</button>
    </form>{error && <p role="alert">{error}</p>}<p role="status">{message}</p><label>Calendar status filter<select value={filter} onChange={e => setFilter(e.target.value)}><option value="ALL">All events</option>{(['PLANNED', 'OBSERVED', 'INVALIDATED'] as const).map(s => <option key={s}>{s}</option>)}</select></label>
    <div className="table-scroll" tabIndex={0}><table><caption className="sr-only">Dated catalyst assertions for {ticker}</caption><thead><tr><th>Date</th><th>Catalyst / falsification</th><th>Source</th><th>Operator status</th><th>Remove</th></tr></thead><tbody>{ordered.filter(e => filter === 'ALL' || e.status === filter).map(event => <tr key={event.id}><td>{event.date}</td><td className="wrap-cell">{event.title}<small>{event.condition || 'No falsification condition supplied'}</small></td><td>{event.source ? <a href={event.source} target="_blank" rel="noreferrer">Open cited source</a> : 'No source; assumption only'}</td><td><label><span className="sr-only">Status for {event.title}</span><select value={event.status} onChange={e => persist(events.map(item => item.id === event.id ? {...item, status: e.target.value as EventStatus} : item))}>{(['PLANNED', 'OBSERVED', 'INVALIDATED'] as const).map(s => <option key={s}>{s}</option>)}</select></label></td><td><button aria-label={`Remove ${event.title}`} onClick={() => persist(events.filter(item => item.id !== event.id))}>Remove</button></td></tr>)}</tbody></table></div>
    {!events.length && <p>No catalyst events saved. Add a dated research question with its source and falsification condition.</p>}
  </section>;
}
