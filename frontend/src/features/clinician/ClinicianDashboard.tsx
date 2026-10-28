import {useEffect, useState} from 'react'
import {useAuth} from '@clerk/react'
import {api, ApiError, type Brief, type Meal, type MedicationEvent} from '../../api/client'
import StatusBadge from '../../components/StatusBadge'

type Profile = {id: string; name: string; timezone: string; summary: string}
type PatientPage = {patients: Profile[]; offset: number; has_more: boolean}
type Detail = {
  patient: Profile; start_date: string; end_date: string; record_limit: number;
  meals: Meal[]; meals_truncated: boolean;
  medication_events: MedicationEvent[]; medication_events_truncated: boolean;
  morning_brief: Brief | null; evening_brief: Brief | null
}

function failureMessage(error: unknown) {
  if (error instanceof ApiError && error.status === 403) return 'Clinician access is unavailable. Your role or account mapping may have changed.'
  if (error instanceof ApiError && error.status === 404) return 'This assigned patient is unavailable. Return to the list to refresh your assignments.'
  return error instanceof Error ? error.message : 'Could not load records. Please try again.'
}

function eventTime(instant: string, timezone: string) {
  try {return `${new Date(instant).toLocaleString(undefined, {timeZone: timezone})} · ${timezone}`}
  catch {return `${instant} (saved timestamp; local display unavailable)`}
}

function SavedBrief({brief, kind}: {brief: Brief | null; kind: string}) {
  return <section className="composer-card brief-card"><h3>Latest saved {kind} brief in range</h3>
    {!brief ? <p className="muted">No saved {kind} brief in this range.</p> : <>
      <p className="muted">{brief.local_day} · {brief.timezone} · Saved {brief.created_at}</p>
      <p className="clinician-narrative">{brief.text}</p><p>{brief.focus_text}</p>
      <details><summary>Based on saved context</summary>
        <p>Captured {brief.context.captured_at}; context window {brief.context.window_start} to {brief.context.window_end}.</p>
        <ul>{brief.context.facts.map(fact => <li key={fact.id}>{fact.text}<div className="brief-sources">Sources: {fact.sources.join(', ')}</div></li>)}</ul>
        <h4>Missing data</h4>{brief.context.missing.length ? <ul>{brief.context.missing.map((item, i) => <li key={i}>{item}</li>)}</ul> : <p>No missing data noted in this snapshot.</p>}
        <h4>Snapshot limits</h4><ul>{brief.context.limits.map((item, i) => <li key={i}>{item}</li>)}</ul>
      </details>
    </>}
  </section>
}

function PatientRecords({patientId, onBack}: {patientId: string; onBack: () => void}) {
  const {getToken} = useAuth()
  const [detail, setDetail] = useState<Detail | null>(null)
  const [error, setError] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [range, setRange] = useState({start: '', end: ''})
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setDetail(null); setError('')
    const query = new URLSearchParams()
    if (range.start) query.set('start_date', range.start)
    if (range.end) query.set('end_date', range.end)
    void (async () => {
      try {
        const result = await api<Detail>(`/api/clinician/patients/${patientId}?${query}`, await getToken(), {signal: controller.signal})
        if (!controller.signal.aborted) {setDetail(result); setStart(result.start_date); setEnd(result.end_date)}
      } catch (failure) {if (!controller.signal.aborted) setError(failureMessage(failure))}
    })()
    return () => controller.abort()
  }, [patientId, range, attempt, getToken])
  return <>
    <button className="text-button" onClick={onBack}>← Assigned patients</button>
    <header className="page-heading"><span className="eyebrow">Read-only synthetic patient records</span>
      <h1>{detail ? detail.patient.name : 'Patient records'}</h1>
      {detail && <><p>{detail.patient.summary}</p><p>Patient timezone: {detail.patient.timezone}</p></>}
    </header>
    <form className="clinician-filters" onSubmit={event => {
      event.preventDefault(); setDetail(null); setError(''); setRange({start, end})
    }}>
      <label>From<input type="date" min="1900-01-01" max="2100-12-31" required value={start} onChange={event => setStart(event.target.value)} /></label>
      <label>Through<input type="date" min={start || '1900-01-01'} max="2100-12-31" required value={end} onChange={event => setEnd(event.target.value)} /></label>
      <button className="primary" type="submit" disabled={!start || !end}>Apply dates</button>
      <button className="text-button" type="button" onClick={() => {setDetail(null); setError(''); setRange({start: '', end: ''})}}>Reset to latest 30 days</button>
      <button className="text-button" type="button" onClick={() => {setDetail(null); setError(''); setAttempt(value => value + 1)}}>Reload saved records</button>
    </form>
    <p className="muted">Up to 90 inclusive days, in the patient's current timezone. Default: the latest 30 days. Saved briefs retain their original timezone and context.</p>
    {error ? <div className="error" role="alert"><p>{error}</p><button className="text-button" onClick={() => setAttempt(value => value + 1)}>Try again</button></div> :
     !detail ? <p role="status">Loading saved records…</p> : <>
      <p className="muted">Showing {detail.start_date} through {detail.end_date}. At most {detail.record_limit} meals and {detail.record_limit} medication events, newest first. These are recorded observations, not clinical assessments.</p>
      <section className="records" aria-labelledby="clinician-meals"><h2 id="clinician-meals">Meals and insights</h2>
        {detail.meals_truncated && <p role="status">More meals exist in this range. Only the newest {detail.record_limit} are shown; narrow the dates to inspect others.</p>}
        {!detail.meals.length && <p className="empty-inline">No recorded meals in this range.</p>}
        {detail.meals.map(meal => <article className="meal-card" key={meal.id}><div className="meal-content">
          <div className="meal-title"><h3>{meal.meal_type}</h3><time>{meal.local_day}</time></div>
          <p className="foods">{meal.foods.map(food => [food.quantity, food.name].filter(Boolean).join(' ')).join(', ')}</p>
          <StatusBadge status={meal.insight_status} />
          {meal.insight_status === 'completed' && meal.insight && <p className="insight">{meal.insight}</p>}
          {meal.insight_status === 'failed' && <p className="muted">The meal is saved; its insight failed.</p>}
          <p className="muted">Revision {meal.revision} · Updated {meal.updated_at}</p>
        </div></article>)}
      </section>
      <section className="records" aria-labelledby="clinician-medications"><h2 id="clinician-medications">Recorded medication events</h2>
        <p className="muted">Missing records do not establish missed doses. Prescription snapshots are references recorded with each event.</p>
        {detail.medication_events_truncated && <p role="status">More events exist in this range. Only the newest {detail.record_limit} are shown; narrow the dates to inspect others.</p>}
        {!detail.medication_events.length && <p className="empty-inline">No recorded medication events in this range.</p>}
        {detail.medication_events.map(item => <article className="meal-card" key={item.id}><div className="meal-content">
          <h3>{item.reported.name?.value || 'Medication report'}</h3>
          <p>Reported strength: {item.reported.strength?.value || 'Not reported'} · Quantity: {item.reported.quantity?.value || 'Not reported'} · Frequency: {item.reported.frequency?.value || 'Not reported'}</p>
          <p><time dateTime={item.occurred_at}>{eventTime(item.occurred_at, detail.patient.timezone)}</time></p>
          <p className="muted">Reference: {item.prescription_snapshot.name} {item.prescription_snapshot.strength} · {item.prescription_snapshot.frequency}</p>
          <p className="muted">{item.synthetic ? 'Synthetic seed event' : 'Patient-reported event'} · Revision {item.revision} · Recorded timezone: {item.timezone}</p>
        </div></article>)}
      </section>
      <SavedBrief brief={detail.morning_brief} kind="morning" /><SavedBrief brief={detail.evening_brief} kind="evening" />
    </>}
  </>
}

export default function ClinicianDashboard() {
  const {getToken} = useAuth()
  const [page, setPage] = useState<PatientPage | null>(null)
  const [offset, setOffset] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<string | null>(null)
  useEffect(() => {
    if (selected) return
    const controller = new AbortController()
    setPage(null); setError('')
    void (async () => {
      try {
        const result = await api<PatientPage>(`/api/clinician/patients?offset=${offset}`, await getToken(), {signal: controller.signal})
        if (!controller.signal.aborted) setPage(result)
      } catch (failure) {if (!controller.signal.aborted) setError(failureMessage(failure))}
    })()
    return () => controller.abort()
  }, [offset, attempt, selected, getToken])
  if (selected) return <PatientRecords key={selected} patientId={selected} onBack={() => {setSelected(null); setPage(null)}} />
  return <>
    <header className="page-heading"><span className="eyebrow">Clinician space · Read only</span><h1>Assigned patients</h1><p>Read existing wellness records for your assigned synthetic profiles.</p></header>
    <button className="text-button" onClick={() => {setPage(null); setError(''); setAttempt(value => value + 1)}}>Refresh assignments</button>
    {error ? <div className="error" role="alert">{error}</div> : !page ? <p role="status">Loading assigned patients…</p> : <>
      {!page.patients.length && <p className="empty-inline">{offset ? 'No assignments on this page. Return to the previous page or refresh.' : 'No assigned patients. A developer can configure synthetic patient assignments using the documented setup commands.'}</p>}
      <div className="clinician-patients">{page.patients.map(patient => <article className="composer-card" key={patient.id}>
        <h2>{patient.name}</h2><p>{patient.summary}</p><p className="muted">{patient.timezone} · Synthetic profile</p>
        <button className="primary" onClick={() => setSelected(patient.id)} aria-label={`View saved records for ${patient.name}`}>View saved records</button>
      </article>)}</div>
      <nav className="feature-navigation" aria-label="Assigned patient pages">
        <button className="text-button" disabled={offset === 0} onClick={() => {setPage(null); setOffset(Math.max(0, offset - 50))}}>Previous</button>
        <span className="muted">Page {Math.floor(offset / 50) + 1}</span>
        <button className="text-button" disabled={!page.has_more || offset >= 10000} onClick={() => {setPage(null); setOffset(offset + 50)}}>Next</button>
      </nav>
      {page.has_more && offset >= 10000 && <p className="muted">More assignments exist beyond this dashboard's page limit. This list is incomplete.</p>}
    </>}
  </>
}
