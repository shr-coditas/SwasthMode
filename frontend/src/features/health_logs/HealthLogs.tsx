import {useCallback, useEffect, useRef, useState} from 'react'
import {useAuth} from '@clerk/react'
import {api, type HealthPayload, type HealthReply, type HealthConversation} from '../../api/client'
import VoiceRecorder from '../../components/VoiceRecorder'
import SpeechPlayback from '../../components/SpeechPlayback'

export default function HealthLogs({onSaved, visible}: {onSaved: () => void; visible: boolean}) {
  const {getToken} = useAuth()
  const [state, setState] = useState<HealthConversation | null>(null)
  const [text, setText] = useState('')
  const [reply, setReply] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [retry, setRetry] = useState<HealthPayload | null>(null)
  const [clock, setClock] = useState(Date.now())
  const sending = useRef(false)
  const [voiceBusy, setVoiceBusy] = useState(false)
  const [speechId, setSpeechId] = useState<string | null>(null)
  const load = useCallback(async () => {
    const current = await api<HealthConversation>('/api/health-logs/conversation', await getToken())
    setState(current)
    setRetry(current.retry)
    setReply(current.last_result?.reply || '')
    setSpeechId(current.last_result?.request_id || null)
  }, [getToken])
  useEffect(() => {
    void load().catch(failure => setError(failure instanceof Error ? failure.message : 'Could not load unified logging'))
    const timer = window.setInterval(() => setClock(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [load])
  async function send(body: HealthPayload) {
    if (sending.current || voiceBusy) return
    sending.current = true; setBusy(true); setError(''); setRetry(body); setSpeechId(null)
    try {
      const response = await api<HealthReply>('/api/health-logs/messages', await getToken(), {method: 'POST', body: JSON.stringify(body)})
      setRetry(null); setText('')
      // A completed retry can be older than the current question. Recover current
      // controls from the server, never from the replayed response alone.
      await load()
      setReply(`${response.replayed ? 'Recovered response: ' : ''}${response.reply}`)
      setSpeechId(response.request_id)
      onSaved()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Processing paused. Some steps may already be saved. Retry the same request.')
    } finally { sending.current = false; setBusy(false) }
  }
  const workflow = state?.workflow
  const pending = workflow?.pending
  const expired = Boolean(state?.expired || pending && new Date(pending.expires_at).getTime() <= clock)
  const voiceLocked = busy || Boolean(retry) || !state || Boolean(state.interrupted)
  const locked = voiceLocked || voiceBusy
  const active = !expired && Boolean(pending || workflow?.steps.some(step => step.status === 'queued'))
  function payload(action: HealthPayload['action']): HealthPayload {
    return {request_id: crypto.randomUUID(), conversation_id: state?.id || null, action, text: '',
      workflow_id: workflow?.id, step_id: pending?.step_id || workflow?.steps.find(step => step.status === 'queued')?.id,
      question_id: pending?.id, question_version: pending?.question_version ?? state?.version}
  }
  function answer(action: 'confirm' | 'cancel') {
    if (!pending?.medication) return
    const question = pending.medication
    const body = payload(action)
    body.medication = {request_id: body.request_id, conversation_id: pending.specialist_conversation_id,
      text: action, action, question_id: question.id, step_id: question.step_id,
      medication_id: question.medication_id, question_version: question.question_version}
    void send(body)
  }
  return <div className="content-grid"><div className="main-column">
    <section className="composer-card" aria-labelledby="health-log-title">
      <span className="eyebrow">Meals + medication</span><h2 id="health-log-title">One check-in, one step at a time.</h2>
      <p className="muted">Describe up to four clearly separated reports. Medication still needs a complete “I took … now” or “I took … at YYYY-MM-DD HH:MM” statement and your explicit confirmation.</p>
      <form onSubmit={event => {
        event.preventDefault()
        const body = payload(active ? 'answer' : 'report'); body.text = text.trim()
        void send(body)
      }}>
        <label htmlFor="health-log-text">{active && pending ? `Reply to the ${pending.feature === 'meals' ? 'meal' : 'medication'} question` : 'Your meal and medication reports'}</label>
        <textarea id="health-log-text" value={text} rows={4} maxLength={2000}
          placeholder="I had rice and dal for lunch; I took Metformin 500 mg now"
          disabled={locked || active && !pending || Boolean(active && pending?.medication)} onChange={event => setText(event.target.value)} />
        <button className="primary" disabled={locked || !text.trim() || active && !pending || Boolean(active && pending?.medication)}>
          {active && pending ? 'Answer this question' : 'Start logging'}</button>
      </form>
      <VoiceRecorder active={visible} disabled={voiceLocked || Boolean(active && (!pending || pending.medication))}
        onTranscript={setText} onBusyChange={setVoiceBusy} />
      {reply && <p className="reply" aria-live="polite">{reply}</p>}
      {reply && speechId && <SpeechPlayback source={{feature: 'health_logs', source_id: speechId}} active={visible} disabled={busy || voiceBusy} />}
      {expired && <p role="status">This conversation or question expired. Saved records remain. Start a new report; old replies cannot confirm anything.</p>}
      {!expired && pending?.medication && <div className="medication-confirmation">
        <h3>Review this exact medication event</h3><p>{pending.medication.readback}</p>
        <p className="muted">Expires {new Date(pending.expires_at).toLocaleTimeString()}.</p>
        <button className="primary" disabled={locked} onClick={() => answer('confirm')}>Confirm this event</button>
        <button className="text-button" disabled={locked} onClick={() => answer('cancel')}>Cancel this event</button>
      </div>}
      {active && !pending && <button className="primary" disabled={locked} onClick={() => void send(payload('continue'))}>Continue to next report</button>}
      {active && <button className="text-button" disabled={locked} onClick={() => void send(payload('abandon'))}>Stop unfinished steps</button>}
      {error && <p className="error" role="alert">{error}</p>}
      {retry && <div role="status"><p>Processing may have saved a step. Retry the original request to recover its result before starting another.</p>
        <button className="text-button" disabled={busy} onClick={() => void send(retry)}>Retry the same request</button>
        <button className="text-button" disabled={busy} onClick={() => void load().catch(failure => setError(failure instanceof Error ? failure.message : 'Refresh failed'))}>Reload current controls</button></div>}
      {state?.interrupted && !retry && <p role="status">An interrupted request owns this workflow. Recover its original request body or wait for conversation expiry before starting again. Saved records remain visible in the dedicated views.</p>}
      <button className="text-button" disabled={busy || Boolean(retry)} onClick={() => void load().catch(failure => setError(failure instanceof Error ? failure.message : 'Refresh failed'))}>Refresh progress</button>
    </section>
    <section className="records"><h2>This workflow</h2>
      {workflow?.steps.map((step, index) => <article className="meal-card" key={step.id}><div className="meal-content">
        <h3>{index + 1}. {step.feature === 'meals' ? 'Meal' : 'Medication'} <span className="status">{step.status}</span></h3>
        <p>{step.reply || 'Waiting for its turn. Nothing saved for this step yet.'}</p>
        {step.record_id && <p className="muted">Saved record: {step.record_id}</p>}
      </div></article>)}
      {!workflow && <p>No current workflow. Your saved records are available in Meals and Medication events.</p>}
    </section>
  </div><aside className="right-column"><section className="note-card"><h3>Saved steps stay saved.</h3>
    <p>A later clarification or provider failure does not undo an earlier save. Continue processes the next report. Stop leaves saved records in place.</p>
    <p>Use Meals for meal history and Medication events for event history and time corrections. Each view keeps its own conversation.</p>
  </section></aside></div>
}
