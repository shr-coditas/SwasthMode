import {useCallback, useEffect, useRef, useState} from 'react'
import {useAuth} from '@clerk/react'
import {api, type MedicationEvent, type MedicationPayload, type MedicationQuestion, type MedicationReply, type Prescription} from '../../api/client'
import VoiceRecorder from '../../components/VoiceRecorder'
import SpeechPlayback from '../../components/SpeechPlayback'

type Conversation = {id: string | null; expired: boolean; last_reply: string | null; pending: MedicationQuestion | null}

export default function Medications({timezone, active}: {timezone: string; active: boolean}) {
  const {getToken} = useAuth()
  const [events, setEvents] = useState<MedicationEvent[]>([])
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([])
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const [text, setText] = useState('')
  const [reply, setReply] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [correction, setCorrection] = useState<MedicationEvent | null>(null)
  const [clock, setClock] = useState('')
  const [retryBody, setRetryBody] = useState<MedicationPayload | null>(null)
  const sending = useRef(false)
  const [voiceBusy, setVoiceBusy] = useState(false)
  const [speechId, setSpeechId] = useState<string | null>(null)
  const [currentTime, setCurrentTime] = useState(Date.now())

  const load = useCallback(async () => {
    const token = await getToken()
    const [records, references, state] = await Promise.all([
      api<MedicationEvent[]>('/api/medications', token),
      api<Prescription[]>('/api/medications/prescriptions', token),
      api<Conversation>('/api/medications/conversation', token),
    ])
    setEvents(records); setPrescriptions(references); setConversation(state)
    setReply(state.last_reply || '')
    setSpeechId(null)
  }, [getToken])

  useEffect(() => {
    void load().catch(failure => setError(failure instanceof Error ? failure.message : 'Could not load medication records'))
    const timer = window.setInterval(() => setCurrentTime(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [load])

  async function send(body: MedicationPayload) {
    if (sending.current || voiceBusy) return
    sending.current = true; setBusy(true); setError(''); setRetryBody(body); setSpeechId(null)
    try {
      const result = await api<MedicationReply>('/api/medications/messages', await getToken(), {
        method: 'POST', body: JSON.stringify(body),
      })
      setRetryBody(null); setReply(`${result.replayed ? 'Recovered response: ' : ''}${result.reply}`)
      setSpeechId(result.request_id)
      setConversation({id: result.conversation_id, expired: result.status === 'expired', last_reply: result.reply, pending: result.pending})
      setText(''); setCorrection(null); setClock('')
      try { setEvents(await api<MedicationEvent[]>('/api/medications', await getToken())) }
      catch { setError('Your response was received, but the event list could not refresh. Refresh the records to try again.') }
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The medication request failed')
    } finally { sending.current = false; setBusy(false) }
  }

  function payload(action: MedicationPayload['action'], value: string): MedicationPayload {
    return {request_id: crypto.randomUUID(), conversation_id: conversation?.id || null, text: value, action}
  }
  function answer(action: 'confirm' | 'cancel') {
    const question = conversation?.pending
    if (!question) return
    void send({...payload(action, action === 'confirm' ? 'confirm' : 'cancel'), question_id: question.id,
      step_id: question.step_id, medication_id: question.medication_id, question_version: question.question_version})
  }
  const voiceLocked = busy || Boolean(retryBody) || !conversation
  const locked = voiceLocked || voiceBusy
  const pending = conversation?.pending
  const expired = Boolean(pending && new Date(pending.expires_at).getTime() <= currentTime)
  const formatTime = (value: string) => new Intl.DateTimeFormat('en-IN', {dateStyle: 'medium', timeStyle: 'short', timeZone: timezone}).format(new Date(value))

  return <div className="content-grid"><div className="main-column">
    <section className="composer-card" aria-labelledby="medication-composer-title">
      <span className="eyebrow">Medication events</span><h2 id="medication-composer-title">What did you record taking?</h2>
      <p className="muted">Report one medicine already taken. Use “now” or a local YYYY-MM-DD HH:MM time ({timezone}). Review the readback before confirming.</p>
      <form onSubmit={event => {event.preventDefault(); void send(payload('report', text.trim()))}}>
        <label htmlFor="medication-message">Your reported medication event</label>
        <textarea id="medication-message" value={text} maxLength={2000} disabled={locked} rows={4}
          placeholder="I took [medicine name] [strength, if known] now" onChange={event => setText(event.target.value)} />
        <button className="primary" disabled={locked || !text.trim()}>Read back my report</button>
      </form>
      <VoiceRecorder active={active} disabled={voiceLocked} onTranscript={setText} onBusyChange={setVoiceBusy} />
      {reply && <p className="reply" aria-live="polite">{reply}</p>}
      {reply && speechId && <SpeechPlayback source={{feature: 'medications', source_id: speechId}} active={active} disabled={busy || voiceBusy} />}
      {pending && <div className="medication-confirmation">
        <h3>Review this exact event</h3><p>{pending.readback}</p>
        <p className="muted">Confirmation expires {formatTime(pending.expires_at)}.</p>
        {expired ? <p role="status">This confirmation expired. Send a new complete report. No event has been recorded from this question.</p> :
          <div className="medication-controls"><button className="primary" disabled={locked} onClick={() => answer('confirm')}>Confirm this recorded event</button>
            <button className="text-button" disabled={locked} onClick={() => answer('cancel')}>Cancel readback</button></div>}
      </div>}
      {error && <div className="error" role="alert"><p>{error}</p>{retryBody && <>
        <button className="text-button" disabled={busy} onClick={() => void send(retryBody)}>Retry the same request</button>
        <button className="text-button" disabled={busy} onClick={() => {setRetryBody(null); setError('');}}>Edit as a new request</button>
        <p>Retry first if the response was lost: the event may already have been recorded.</p>
      </>}</div>}
    </section>
    <section className="records"><div className="section-heading"><h2>Recorded medication events</h2>
      <button className="text-button" disabled={busy || Boolean(retryBody)} onClick={() => void load().catch(failure => setError(failure instanceof Error ? failure.message : 'Refresh failed'))}>Refresh records</button></div>
      <p className="muted">An absent record does not establish a missed dose. Showing up to 100 recorded events.</p>
      {!events.length && <p className="empty-inline">No medication events are recorded here.</p>}
      {events.map(event => <article className="meal-card" key={event.id}><div className="meal-content">
        <h3>{event.reported.name?.value || 'Reported medication'} {event.synthetic && <span className="status">Synthetic seed</span>}</h3>
        <p>Recorded time: <time dateTime={event.occurred_at}>{formatTime(event.occurred_at)}</time></p>
        <p className="foods">Reported strength: {event.reported.strength?.value || 'not reported'}; quantity: {event.reported.quantity?.value || 'not reported'}; frequency: {event.reported.frequency?.value || 'not reported'}.</p>
        <p className="muted">Prescription reference: {event.prescription_snapshot.name}, {event.prescription_snapshot.strength}, {event.prescription_snapshot.frequency}.</p>
        <button className="text-button" disabled={locked} onClick={() => {setCorrection(event); setClock('');}}>Correct recorded time</button>
      </div></article>)}
      {correction && <form className="composer-card" onSubmit={event => {
        event.preventDefault()
        void send({...payload('correct_time', clock.replace('T', ' ')), event_id: correction.id, event_revision: correction.revision})
      }}><h3>Correct recorded time for {correction.prescription_snapshot.name}</h3>
        <label htmlFor="medication-clock">Local date and time ({timezone})</label>
        <input id="medication-clock" type="datetime-local" value={clock} disabled={locked} required onChange={event => setClock(event.target.value)} />
        <p className="muted">Only the event time can change. A readback will ask you to confirm.</p>
        <button className="primary" disabled={locked || !clock}>Read back time correction</button>
        <button className="text-button" type="button" disabled={locked} onClick={() => setCorrection(null)}>Cancel correction</button>
      </form>}
    </section>
  </div><aside className="right-column"><section className="day-card"><span className="eyebrow">Your prescription references</span>
    <p>These are synthetic reference records, not directions from this app.</p>
    {prescriptions.map(item => <p key={item.id}><strong>{item.name}</strong><br />{item.strength} · {item.frequency}</p>)}
  </section><section className="note-card"><h3>Your words stay visible.</h3><p>Reported details and prescription reference details are kept separately. If the readback is uncertain or incorrect, cancel and send a new complete report.</p></section></aside></div>
}
