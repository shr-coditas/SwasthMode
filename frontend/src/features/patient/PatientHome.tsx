import {useCallback, useEffect, useState} from 'react'
import {useAuth} from '@clerk/react'
import {api, type Account, type Meal, type Reply} from '../../api/client'
import Composer from '../../components/Composer'
import Timeline from '../../components/Timeline'
import Medications from '../medications/Medications'
import Briefs from '../briefs/Briefs'
import HealthLogs from '../health_logs/HealthLogs'

export default function PatientHome({account}: {account: Account}) {
  const {getToken} = useAuth()
  const [meals, setMeals] = useState<Meal[]>([])
  const [conversation, setConversation] = useState<string | null>(null)
  const [lastReply, setLastReply] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [loaded, setLoaded] = useState(false)
  const [composer, setComposer] = useState({key: 0, text: ''})
  const [view, setView] = useState<'meals' | 'medications' | 'briefs' | 'health_logs'>('health_logs')
  const timezone = account.patient!.timezone
  const today = new Intl.DateTimeFormat('en-CA', {timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date())
  const loadMeals = useCallback(async () => {
    try { setMeals(await api<Meal[]>('/api/meals', await getToken())); setError('') }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'Could not load meals') }
  }, [getToken])
  useEffect(() => {
    let active = true
    void (async () => {
      try {
        const state = await api<{id: string | null; expired: boolean; last_reply: string | null}>('/api/meals/conversation', await getToken())
        if (!active) return
        setConversation(state.expired ? null : state.id)
        setLastReply(state.expired ? 'Your previous meal conversation expired. Saved meals remain.' : state.last_reply)
      } catch (failure) { if (active) setError(failure instanceof Error ? failure.message : 'Could not load conversation') }
      finally { if (active) setLoaded(true) }
    })()
    void loadMeals()
    const interval = window.setInterval(() => void loadMeals(), 15000)
    return () => { active = false; clearInterval(interval) }
  }, [getToken, loadMeals])
  function received(reply: Reply) { setConversation(reply.conversation_id); void loadMeals() }
  const todaysMeals = meals.filter(meal => meal.local_day === today)
  return <>
    <header className="page-heading"><span className="eyebrow">Your daily rhythm</span>
      <h1>Small moments.<br /><em>A little more awareness.</em></h1>
      <p>Welcome, {account.patient!.name}. Make space for a simple check-in.</p>
      <span className="date-pill">{new Intl.DateTimeFormat('en-IN', {dateStyle: 'full', timeZone: timezone}).format(new Date())}</span>
    </header>
    <nav className="feature-navigation" aria-label="Patient logging views">
      <button className={view === 'health_logs' ? 'primary' : 'text-button'} aria-current={view === 'health_logs' ? 'page' : undefined} onClick={() => setView('health_logs')}>Meals + medication</button>
      <button className={view === 'meals' ? 'primary' : 'text-button'} aria-current={view === 'meals' ? 'page' : undefined} onClick={() => setView('meals')}>Meals</button>
      <button className={view === 'medications' ? 'primary' : 'text-button'} aria-current={view === 'medications' ? 'page' : undefined} onClick={() => setView('medications')}>Medication events</button>
      <button className={view === 'briefs' ? 'primary' : 'text-button'} aria-current={view === 'briefs' ? 'page' : undefined} onClick={() => setView('briefs')}>Daily briefs</button>
    </nav>
    <div hidden={view !== 'health_logs'}><HealthLogs visible={view === 'health_logs'} onSaved={() => void loadMeals()} /></div>
    <div hidden={view !== 'medications'}><Medications timezone={timezone} active={view === 'medications'} /></div>
    <div hidden={view !== 'briefs'}><Briefs active={view === 'briefs'} /></div>
    <div hidden={view !== 'meals'}><div className="content-grid"><div className="main-column">
      {loaded ? <Composer key={composer.key} initialText={composer.text} initialReply={lastReply} active={view === 'meals'}
        conversationId={conversation} onReply={received} onExpired={() => setConversation(null)} /> : <p role="status">Loading your conversation…</p>}
      <section className="records"><div className="section-heading"><div><span className="eyebrow">Your recorded moments</span><h2>Meal timeline</h2></div>
        <button className="text-button" onClick={() => void loadMeals()}>Refresh ↻</button></div>
        {error && <p className="error" role="alert">{error}</p>}
        <Timeline meals={meals} today={today} onCorrect={meal => {
          setComposer(current => ({key: current.key + 1, text: `For my ${meal.meal_type} on ${meal.local_day} (${meal.foods.map(f => f.name).join(', ')}), change `}))
          document.getElementById('composer-title')?.scrollIntoView({behavior: 'smooth'})
        }} />
      </section>
    </div><aside className="right-column">
      <section className="day-card"><span className="eyebrow">Today, at a glance</span><div className="big-number">{todaysMeals.length}<span>meals recorded</span></div>
        <p>Each entry adds a little context to your day.</p><span className="tiny">{timezone}</span></section>
      <section className="note-card"><span aria-hidden="true">✳</span><h3>Keep it simple.</h3><p>Start with what you ate. Add the meal type when asked. You can make a correction in the same conversation.</p></section>
      <section className="coming-card"><span className="eyebrow">Next in the POC</span><p>Read-only clinician detail views are planned in a following slice.</p></section>
    </aside></div></div>
  </>
}
