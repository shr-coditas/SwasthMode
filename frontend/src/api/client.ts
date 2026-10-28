export type Food = { name: string; quantity: string | null; evidence: string }
export type Meal = {
  id: string; local_day: string; meal_type: string; foods: Food[]; revision: number;
  insight_status: string; insight: string | null; created_at: string; updated_at: string
}
export type Account = {
  setup_required: boolean; role: 'patient' | 'clinician' | null;
  patient: { id: string; name: string; timezone: string; summary: string } | null;
  assigned_patient_count?: number
}
export type MealPayload = {request_id: string; text: string; conversation_id: string | null}
export type Reply = {
  request_id: string; conversation_id: string; status: 'saved' | 'clarification' | 'reply';
  reply: string; meal: Meal | null; replayed: boolean
}
export type ReportedField = {value: string; evidence: string}
export type Prescription = {id: string; name: string; strength: string; frequency: string}
export type MedicationEvent = {
  id: string; prescription_id: string; prescription_snapshot: Prescription;
  reported: {name: ReportedField | null; strength: ReportedField | null; quantity: ReportedField | null; frequency: ReportedField | null};
  occurred_at: string; timezone: string; time_evidence: string; revision: number; synthetic: boolean;
  created_at: string; updated_at: string
}
export type MedicationQuestion = {
  id: string; step_id: string; medication_id: string; question_version: number; expires_at: string; readback: string
}
export type MedicationPayload = {
  request_id: string; conversation_id: string | null; text: string;
  action: 'report' | 'confirm' | 'cancel' | 'correct_time';
  question_id?: string; step_id?: string; medication_id?: string; question_version?: number;
  event_id?: string; event_revision?: number
}
export type MedicationReply = {
  request_id: string; conversation_id: string; status: string; reply: string;
  pending: MedicationQuestion | null; event: MedicationEvent | null; replayed: boolean
}
export type BriefKind = 'morning' | 'evening'
export type HealthPayload = {
  request_id: string; conversation_id: string | null; text: string;
  action: 'report' | 'answer' | 'confirm' | 'cancel' | 'continue' | 'abandon';
  workflow_id?: string; step_id?: string; question_id?: string; question_version?: number;
  medication?: MedicationPayload
}
export type HealthPending = {
  id: string; step_id: string; feature: 'meals' | 'medications'; question_version: number;
  expires_at: string; medication: MedicationQuestion | null; specialist_conversation_id: string | null
}
export type HealthStep = {
  id: string; feature: 'meals' | 'medications'; status: string; reply: string; record_id: string | null
}
export type HealthReply = {
  request_id: string; conversation_id: string; workflow_id: string | null; version: number;
  status: string; reply: string; steps: HealthStep[]; pending: HealthPending | null; replayed: boolean
}
export type HealthConversation = {
  id: string | null; version?: number; expired: boolean; last_result: HealthReply | null;
  workflow?: {id: string; steps: HealthStep[]; pending: HealthPending | null} | null;
  retry: HealthPayload | null; interrupted?: boolean
}
export type BriefPayload = {request_id: string; kind: BriefKind}
export type Brief = {
  id: string; kind: BriefKind; local_day: string; timezone: string; created_at: string;
  text: string; focus_text: string;
  context: {
    captured_at: string; window_start: string; window_end: string;
    facts: {id: string; text: string; sources: string[]}[]; missing: string[]; limits: string[]
  }
}
export type BriefReply = {
  request_id: string; status: 'saved' | 'reused'; reply: string; brief: Brief;
  reused: boolean; replayed: boolean; reuse_until: string
}
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

const base = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export type SpeechSource = {feature: 'meals' | 'medications' | 'health_logs' | 'briefs'; source_id: string}

async function speechRequest(path: string, token: string | null, init: RequestInit) {
  if (!token) throw new ApiError(401, 'Your session ended. Please sign in again.')
  const response = await fetch(`${base}/api/speech/${path}`, {
    ...init, signal: AbortSignal.any([init.signal || new AbortController().signal, AbortSignal.timeout(90000)]),
    headers: {...init.headers, Authorization: `Bearer ${token}`},
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, response.status === 401 ? 'Session expired. Sign in again.' :
      typeof body.detail === 'string' ? body.detail : 'Speech request failed. Text remains available.')
  }
  return response
}

export async function transcribeAudio(token: string | null, audio: Blob, signal: AbortSignal): Promise<string> {
  const response = await speechRequest('transcriptions', token, {
    method: 'POST', body: audio, headers: {'Content-Type': audio.type}, signal,
  })
  const body = await response.json() as {text: string}
  return body.text
}

export async function speechAudio(token: string | null, source: SpeechSource, signal: AbortSignal): Promise<Blob> {
  const response = await speechRequest('audio', token, {
    method: 'POST', body: JSON.stringify(source), headers: {'Content-Type': 'application/json'}, signal,
  })
  return response.blob()
}

export async function api<T>(path: string, token: string | null, init: RequestInit = {}): Promise<T> {
  if (!token) throw new ApiError(401, 'Your session ended. Please sign in again.')
  const response = await fetch(`${base}${path}`, { ...init, headers: {
    ...init.headers, Authorization: `Bearer ${token}`, 'Content-Type': 'application/json',
  } })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, response.status === 401 ?
      'Your session expired or could not be verified. Please sign in again.' :
      typeof body.detail === 'string' ? body.detail : 'The request could not be completed.')
  }
  return response.json() as Promise<T>
}

export async function sendMeal(token: string | null, body: MealPayload, onText: (text: string) => void): Promise<Reply> {
  if (!token) throw new ApiError(401, 'Your session ended. Please sign in again.')
  const response = await fetch(`${base}/api/meals/messages?stream=true`, {
    method: 'POST', headers: {Authorization: `Bearer ${token}`, 'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new ApiError(response.status, response.status === 401 ? 'Session expired. Sign in again.' :
      typeof error.detail === 'string' ? error.detail : 'The meal request failed.')
  }
  if (!response.body) throw new Error('The reply stream was interrupted. Retry the same message.')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let text = ''
  let result: Reply | null = null
  while (true) {
    const {done, value} = await reader.read()
    buffer += decoder.decode(value, {stream: !done})
    let boundary: number
    while ((boundary = buffer.indexOf('\n\n')) >= 0) {
      const frame = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      const data = frame.split('\n').find(line => line.startsWith('data: '))?.slice(6)
      if (!data) continue
      if (frame.startsWith('event: text')) { text += JSON.parse(data).text; onText(text) }
      if (frame.startsWith('event: result')) result = JSON.parse(data) as Reply
    }
    if (done) break
  }
  if (!result) throw new Error('The final result was interrupted. Retry the same message to recover it.')
  return result
}
