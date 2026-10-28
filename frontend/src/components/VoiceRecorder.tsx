import {useEffect, useId, useRef, useState} from 'react'
import {useAuth} from '@clerk/react'
import {transcribeAudio} from '../api/client'

const mime = 'audio/webm;codecs=opus'
const maxBytes = 2 * 1024 * 1024

export default function VoiceRecorder({active, disabled, onTranscript, onBusyChange}: {
  active: boolean; disabled: boolean; onTranscript: (text: string) => void; onBusyChange: (busy: boolean) => void
}) {
  const {getToken} = useAuth()
  const id = useId()
  const [supported, setSupported] = useState(false)
  const [phase, setPhase] = useState<'idle' | 'permission' | 'recording' | 'transcribing'>('idle')
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState('')
  const resources = useRef<{epoch: number; recorder?: MediaRecorder; stream?: MediaStream;
    timer?: number; abort?: AbortController}>({epoch: 0})
  const running = useRef(false)

  function release() {
    const current = resources.current
    window.clearTimeout(current.timer)
    if (current.recorder?.state === 'recording') current.recorder.stop()
    current.stream?.getTracks().forEach(track => track.stop())
    current.recorder = undefined; current.stream = undefined; current.timer = undefined
  }
  function cancel() {
    resources.current.epoch++
    resources.current.abort?.abort()
    release(); running.current = false; setPhase('idle'); onBusyChange(false)
  }
  useEffect(() => {
    setSupported(window.isSecureContext && Boolean(navigator.mediaDevices?.getUserMedia) &&
      typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(mime))
    return () => {
      resources.current.epoch++; resources.current.abort?.abort(); release(); onBusyChange(false)
    }
  }, [onBusyChange])
  useEffect(() => { if (!active || disabled) cancel() }, [active, disabled])

  async function start() {
    if (running.current || disabled || !active) return
    running.current = true; onBusyChange(true); setPhase('permission'); setError(''); setTranscript('')
    document.querySelectorAll('audio').forEach(audio => audio.pause())
    const epoch = ++resources.current.epoch
    let chunks: Blob[] = []
    let size = 0
    try {
      const stream = await navigator.mediaDevices.getUserMedia({audio: true})
      if (epoch !== resources.current.epoch) { stream.getTracks().forEach(track => track.stop()); return }
      resources.current.stream = stream
      const recorder = new MediaRecorder(stream, {mimeType: mime, audioBitsPerSecond: 64000})
      resources.current.recorder = recorder
      recorder.ondataavailable = event => {
        if (epoch !== resources.current.epoch) return
        size += event.data.size
        if (size > maxBytes) {
          chunks = []; cancel(); setError('Recording exceeded 2 MiB. Try a shorter message.'); return
        }
        if (event.data.size) chunks.push(event.data)
      }
      recorder.onerror = () => {
        if (epoch !== resources.current.epoch) return
        chunks = []; cancel(); setError('Microphone recording failed. Type your message or try again.')
      }
      recorder.onstop = () => {
        if (epoch !== resources.current.epoch) { chunks = []; return }
        release()
        const recording = new Blob(chunks, {type: recorder.mimeType})
        chunks = []
        if (!recording.size) { cancel(); setError('No audio was captured. Try again.'); return }
        const abort = new AbortController(); resources.current.abort = abort
        setPhase('transcribing')
        void (async () => {
          try {
            const text = await transcribeAudio(await getToken(), recording, abort.signal)
            if (epoch === resources.current.epoch) setTranscript(text)
          } catch (failure) {
            if (epoch === resources.current.epoch) setError(failure instanceof Error ? failure.message : 'Transcription failed. Type your message or record again.')
          } finally {
            if (epoch === resources.current.epoch) { running.current = false; setPhase('idle'); onBusyChange(false) }
          }
        })()
      }
      recorder.start(250); setPhase('recording')
      resources.current.timer = window.setTimeout(() => {
        if (epoch === resources.current.epoch && recorder.state === 'recording') recorder.stop()
      }, 60000)
    } catch (failure) {
      if (epoch !== resources.current.epoch) return
      cancel(); setError(failure instanceof DOMException && failure.name === 'NotAllowedError' ?
        'Microphone permission was denied. Allow microphone access in Chrome or type your message.' :
        'Microphone unavailable. Use desktop Chrome on localhost or HTTPS, or type your message.')
    }
  }
  return <div className="voice-controls">
    <p className="muted">Voice input · desktop Chrome · up to 60 seconds. Stopping sends audio to the transcription provider. Nothing is logged until you submit the message.</p>
    {!supported ? <p>Voice recording needs desktop Chrome with WebM/Opus and microphone access on localhost or HTTPS. You can still type.</p> : <>
      {phase === 'idle' ? <button className="text-button" type="button" disabled={disabled || !active} onClick={() => void start()}>Record a message</button> : <>
        <span role="status">{phase === 'permission' ? 'Waiting for microphone permission…' : phase === 'recording' ? 'Recording… stops automatically at 60 seconds.' : 'Transcribing…'}</span>
        {phase === 'recording' && <button className="text-button" type="button" onClick={() => {
          if (resources.current.recorder?.state === 'recording') resources.current.recorder.stop()
        }}>Stop and transcribe</button>}
        <button className="text-button" type="button" onClick={cancel}>Cancel voice input</button>
      </>}
    </>}
    {transcript && <div className="transcript-review"><label htmlFor={id}>Review the transcript — check medicine names, strengths, quantities and times</label>
      <textarea id={id} rows={3} maxLength={2000} value={transcript} disabled={disabled} onChange={event => setTranscript(event.target.value)} />
      <button className="text-button" type="button" disabled={disabled || !active || !transcript.trim()} onClick={() => {onTranscript(transcript.trim()); setTranscript('')}}>Replace message with this transcript</button>
      <button className="text-button" type="button" disabled={disabled} onClick={() => setTranscript('')}>Discard transcript</button>
    </div>}
    {error && <p className="error" role="alert">{error}</p>}
  </div>
}
