import {useCallback, useEffect, useState} from 'react'
import {useAuth} from '@clerk/react'
import {api, type Brief, type BriefKind, type BriefPayload, type BriefReply} from '../../api/client'
import SpeechPlayback from '../../components/SpeechPlayback'

function clock(value: string, timezone: string) {
  return new Intl.DateTimeFormat('en-IN', {timeZone: timezone, dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value))
}

function BriefCard({brief, active}: {brief: Brief; active: boolean}) {
  return <article className="composer-card brief-card">
    <span className="eyebrow">{brief.kind} brief · {brief.local_day}</span>
    <h3>From your recorded moments</h3>
    <p className="muted">Saved {clock(brief.created_at, brief.timezone)} · {brief.timezone}</p>
    <p>{brief.text}</p>
    <h3>A small focus</h3><p>{brief.focus_text}</p>
    <SpeechPlayback source={{feature: 'briefs', source_id: brief.id}} active={active} />
    <h3>Missing data</h3>
    {brief.context.missing.length ? <ul>{brief.context.missing.map(item => <li key={item}>{item}</li>)}</ul> : <p>No gaps in the supported measurement fields for this window.</p>}
    <details><summary>Based on · {brief.context.window_start} to {brief.context.window_end}</summary>
      <p className="muted">Snapshot captured {clock(brief.context.captured_at, brief.timezone)}. Later records and corrections are not included.</p>
      <ul>{brief.context.facts.map(fact => <li key={fact.id}>{fact.text}
        {fact.sources.length > 0 && <details><summary>Record references ({fact.sources.length})</summary>
          <ul className="brief-sources">{fact.sources.map(source => <li key={source}>{source}</li>)}</ul>
        </details>}
      </li>)}</ul>
    </details>
    <h3>Context limits</h3><ul>{brief.context.limits.map(item => <li key={item}>{item}</li>)}</ul>
    <p className="muted">{brief.kind === 'morning' ? 'Reuse: this patient-local day.' : 'Reuse: 30 minutes from saving, ending at local midnight if earlier.'} Reuse keeps this original snapshot.</p>
  </article>
}

export default function Briefs({active}: {active: boolean}) {
  const {getToken} = useAuth()
  const [history, setHistory] = useState<Brief[]>([])
  const [pending, setPending] = useState<BriefPayload | null>(null)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [historyError, setHistoryError] = useState('')
  const [result, setResult] = useState<BriefReply | null>(null)
  const load = useCallback(async () => {
    try { setHistory(await api<Brief[]>('/api/briefs', await getToken())); setHistoryError('') }
    catch (failure) { setHistoryError(failure instanceof Error ? failure.message : 'Could not load briefs') }
    finally { setLoading(false) }
  }, [getToken])
  useEffect(() => { void load() }, [load])
  async function send(body: BriefPayload) {
    setPending(body); setBusy(true); setError('')
    try {
      const reply = await api<BriefReply>('/api/briefs', await getToken(), {method: 'POST', body: JSON.stringify(body)})
      setResult(reply); setPending(null); void load()
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Could not generate a brief') }
    finally { setBusy(false) }
  }
  function request(kind: BriefKind) { void send({request_id: crypto.randomUUID(), kind}) }
  return <section className="records" aria-labelledby="briefs-title">
    <div className="section-heading"><div><span className="eyebrow">A moment to notice</span><h2 id="briefs-title">Morning & evening briefs</h2></div>
      <button className="text-button" disabled={busy} onClick={() => void load()}>Refresh saved briefs</button></div>
    <p className="muted">Morning looks at the previous seven complete local days. Evening looks at today so far. Requests within the reuse window return the saved snapshot.</p>
    <div className="feature-navigation">
      <button className="primary" disabled={busy || !!pending} onClick={() => request('morning')}>Morning brief</button>
      <button className="primary" disabled={busy || !!pending} onClick={() => request('evening')}>Evening brief</button>
    </div>
    {busy && <p role="status">Preparing your brief…</p>}
    {error && <div className="error" role="alert"><p>{error}</p>
      {pending && <><button className="text-button" disabled={busy} onClick={() => void send(pending)}>Retry the same request</button>
        <button className="text-button" disabled={busy} onClick={() => { setPending(null); setError('') }}>Start a new request</button>
        <p>A lost response may already have saved a brief. Retry first to recover its result. Starting again uses a new request ID.</p></>}
    </div>}
    {result && <div className="brief-result" role="status"><strong>{result.replayed ? 'Recovered original result' : result.reused ? 'Reused saved brief' : 'Brief saved'}</strong>
      <p>{result.reply} Saved {clock(result.brief.created_at, result.brief.timezone)}. Original reuse window ends {clock(result.reuse_until, result.brief.timezone)}.</p>
      {result.replayed && <p>This is the original request result, even if its reuse window has since ended.</p>}
    </div>}
    {result && <BriefCard brief={result.brief} active={active} />}
    {historyError && <p className="error" role="alert">{historyError}</p>}
    {loading ? <p role="status">Loading saved briefs…</p> : <p className="muted">Latest {history.length} saved briefs, up to 30. History does not generate new text.</p>}
    {history.filter(brief => brief.id !== result?.brief.id).map(brief => <BriefCard key={brief.id} brief={brief} active={active} />)}
  </section>
}
