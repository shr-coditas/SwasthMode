import {useRef, useState} from 'react'
import {useAuth} from '@clerk/react'
import {ApiError, sendMeal, type MealPayload, type Reply} from '../api/client'
import StatusBadge from './StatusBadge'
import VoiceRecorder from './VoiceRecorder'
import SpeechPlayback from './SpeechPlayback'

export default function Composer({active, conversationId, initialText, initialReply, onReply, onExpired}: {
  active: boolean;
  conversationId: string | null; initialText: string; initialReply: string | null;
  onReply: (reply: Reply) => void; onExpired: () => void
}) {
  const {getToken} = useAuth()
  const [text, setText] = useState(initialText)
  const [busy, setBusy] = useState(false)
  const [reply, setReply] = useState(initialReply || '')
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const pending = useRef<MealPayload | null>(null)
  const sending = useRef(false)
  const [voiceBusy, setVoiceBusy] = useState(false)
  const [speechId, setSpeechId] = useState<string | null>(null)

  async function submit(retry = false) {
    if (sending.current || voiceBusy || (!retry && !text.trim())) return
    sending.current = true
    const payload = retry && pending.current ? pending.current : {
      request_id: crypto.randomUUID(), text: text.trim(), conversation_id: conversationId,
    }
    pending.current = payload
    setBusy(true); setError(''); setReply(''); setStatus(''); setSpeechId(null)
    try {
      const result = await sendMeal(await getToken(), payload, setReply)
      pending.current = null
      setSpeechId(result.request_id)
      setReply(result.reply); setStatus(result.replayed ? 'Recovered saved response' : result.status)
      setText(''); onReply(result)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The request failed.')
      if (failure instanceof ApiError && failure.status === 409 && /expired|ended|older conversation/.test(failure.message)) {
        pending.current = null; onExpired()
      }
    } finally { setBusy(false); sending.current = false }
  }

  return <section className="composer-card" aria-labelledby="composer-title">
    <div className="section-top"><span className="eyebrow">A moment to check in</span><span className="small-label">Text + voice</span></div>
    <h2 id="composer-title">What was on your plate?</h2>
    <p className="muted">Tell me in your own words. We can fill in the details together.</p>
    <form onSubmit={event => {event.preventDefault(); void submit()}}>
      <label className="sr-only" htmlFor="meal-message">Describe your meal or correction</label>
      <textarea id="meal-message" maxLength={2000} value={text} disabled={busy || voiceBusy || Boolean(pending.current)}
        placeholder="I had rice and dal for lunch…" onChange={event => setText(event.target.value)} rows={4} />
      <div className="composer-actions"><span>Only explicitly reported foods and quantities.</span>
        <button className="primary" type="submit" disabled={busy || voiceBusy || !text.trim() || Boolean(pending.current)}>
          {busy ? 'Working on your message…' : 'Send message ↗'}</button></div>
    </form>
    <VoiceRecorder active={active} disabled={busy || Boolean(pending.current)} onTranscript={setText} onBusyChange={setVoiceBusy} />
    {error && <div className="error" role="alert"><p>{error}</p>
      {pending.current && <><button className="text-button" disabled={busy} onClick={() => void submit(true)}>Retry the same request</button>
        <button className="text-button" disabled={busy} onClick={() => {pending.current = null; setError('');}}>Edit as a new message</button>
        <p className="muted">A lost reply may follow a successful save. Retry first to recover the result without duplicating it.</p></>}
    </div>}
    {reply && <div className="reply" aria-live="polite"><span className="reply-icon" aria-hidden="true">✳</span>
      <div>{status && <StatusBadge status={status} />}<p>{reply}</p>
        {speechId && <SpeechPlayback source={{feature: 'meals', source_id: speechId}} active={active} disabled={busy || voiceBusy} />}</div></div>}
  </section>
}
