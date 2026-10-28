import React from 'react'
import ReactDOM from 'react-dom/client'
import { ClerkProvider } from '@clerk/react'
import App from './App'
import './styles.css'

const key = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {key && !key.startsWith('replace_') ? <ClerkProvider publishableKey={key} afterSignOutUrl="/">
      <App />
    </ClerkProvider> : <main className="configuration"><span className="brand">SwasthMode</span>
      <h1>A little setup before we begin.</h1>
      <p>Add your Clerk development publishable key to the frontend configuration, then restart the frontend.</p>
      <p>See README.md for the local setup steps.</p>
    </main>}
  </React.StrictMode>,
)
