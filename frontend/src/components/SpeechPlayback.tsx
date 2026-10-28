import {useEffect, useRef, useState} from 'react'
import {useAuth} from '@clerk/react'
import {speechAudio, type SpeechSource} from '../api/client'

export default function SpeechPlayback({source, active, disabled = false}: {
  source: SpeechSource; active: boolean; disabled?: boolean
}) {
  const {getToken} = useAuth()
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const audio = useRef<HTMLAudioElement>(null)
  const request = useRef<AbortController | null>(null)
  const localUrl = useRef('')
  useEffect(() => {
    setUrl(''); setBusy(false); setError('')
    return () => {
      request.current?.abort(); request.current = null
      audio.current?.pause()
      URL.revokeObjectURL(localUrl.current); localUrl.current = ''
    }
  }, [source.feature, source.source_id, active, disabled])
  async function generate() {
    if (request.current || disabled || !active) return
    const controller = new AbortController(); request.current = controller
    setBusy(true); setError('')
    try {
      const blob = await speechAudio(await getToken(), source, controller.signal)
      if (controller.signal.aborted) return
      localUrl.current = URL.createObjectURL(blob); setUrl(localUrl.current)
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : 'Speech failed. The text remains available.')
    } finally {
      if (!controller.signal.aborted) {request.current = null; setBusy(false)}
    }
  }
  return <div className="speech-playback">
    {!url && <button className="text-button" type="button" disabled={busy || disabled || !active} onClick={() => void generate()}>{busy ? 'Preparing audio…' : 'Listen · AI-generated voice'}</button>}
    {url && <><p className="muted">AI-generated voice · Cartesia. This reads a saved response; its question may have expired. Use the current written readback to confirm medication details.</p>
      <audio ref={audio} controls preload="none" src={url} onPlay={() => {
        document.querySelectorAll('audio').forEach(other => {if (other !== audio.current) other.pause()})
      }} onError={() => {URL.revokeObjectURL(localUrl.current); localUrl.current = ''; setUrl(''); setError('Audio playback failed. Read the text or prepare audio again.')}} /></>}
    {error && <p className="error" role="alert">{error}</p>}
  </div>
}
