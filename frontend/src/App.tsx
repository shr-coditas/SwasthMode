import {useEffect, useState} from 'react'
import {Show, SignIn, UserButton, useAuth} from '@clerk/react'
import {api, type Account} from './api/client'
import AccountSetup from './features/account/AccountSetup'
import PatientHome from './features/patient/PatientHome'
import ClinicianDashboard from './features/clinician/ClinicianDashboard'

function Workspace() {
  const {getToken} = useAuth()
  const [account, setAccount] = useState<Account | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setAccount(null); setError('')
    void (async () => {
      try {
        const result = await api<Account>('/api/account', await getToken(), {signal: controller.signal})
        if (!controller.signal.aborted) setAccount(result)
      } catch (failure) {
        if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : 'Could not load account')
      }
    })()
    return () => controller.abort()
  }, [getToken, attempt])
  return <div className="app-shell">
    <aside className="sidebar"><a className="brand" href="/" aria-label="SwasthMode home"><span className="brand-mark">✳</span>SwasthMode<span className="brand-dot">.</span></a>
      <span className="nav-label">YOUR SPACE</span>
      <nav aria-label="Main navigation"><a className="nav-active" href="/">◒ <span>{account?.role === 'clinician' ? 'Clinician space' : 'Daily check-in'}</span></a></nav>
      <div className="sidebar-bottom"><span className="demo-badge">Synthetic data · POC</span><p>A calmer way to keep track.</p><div className="user-row"><UserButton /><span>Your Clerk account</span></div></div>
    </aside>
    <main className="workspace"><div className="topbar"><span>WELLNESS, ONE DAY AT A TIME</span><span className="pill">Meals · Medication events · Briefs</span></div>
      {error ? <section className="empty-card" role="alert"><h1>We couldn’t open your space.</h1><p>{error}</p><p>Use the account control to sign out if your session has expired.</p><button className="primary" onClick={() => setAttempt(value => value + 1)}>Try again</button></section> :
       !account ? <p role="status">Loading your account…</p> : account.setup_required ? <AccountSetup /> :
       account.role === 'patient' && account.patient ? <PatientHome account={account} /> :
       account.role === 'clinician' ? <ClinicianDashboard /> : <AccountSetup />}
      <footer>SwasthMode · Independent wellness demonstration · Synthetic profiles, real AI.</footer>
    </main>
  </div>
}

export default function App() {
  const {userId, sessionId} = useAuth()
  return <><Show when="signed-out"><main className="login-layout"><section className="login-story"><span className="brand"><span className="brand-mark">✳</span>SwasthMode.</span>
    <span className="eyebrow">A little attention, every day</span><h1>Find your<br /><em>daily rhythm.</em></h1><p>A simple space to record meals, notice patterns, and build awareness.</p><div className="login-art" aria-hidden="true"><span /><span /><span /></div><span className="demo-badge">Independent POC · Synthetic patient data</span></section><section className="signin-panel"><SignIn routing="hash" /></section></main></Show><Show when="signed-in"><Workspace key={`${userId}:${sessionId}`} /></Show></>
}
