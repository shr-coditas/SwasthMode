export default function AccountSetup() {
  return <section className="empty-card"><span className="eyebrow">One more step</span>
    <h1>Let’s connect your demo profile.</h1>
    <p>You’re signed in. A developer needs to associate this account with a synthetic patient or assign the clinician role.</p>
    <p>Follow the account-mapping commands in README.md, then reload this page.</p>
    <button className="primary" onClick={() => location.reload()}>Check account setup</button>
  </section>
}
