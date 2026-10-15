import { useState } from 'react';
import Heartbeat from './Heartbeat';

// NFR-02: the laptop is only checked after the owner agrees.
// The answer is kept in this browser so we do not ask every time.
const KEY = 'kayvak-consent';

function readConsent() {
  try {
    return localStorage.getItem(KEY) === 'yes';
  } catch {
    return false;
  }
}

function ConsentGate({ children }) {
  const [agreed, setAgreed] = useState(readConsent);

  const agree = () => {
    try {
      localStorage.setItem(KEY, 'yes');
    } catch {
      // if the browser blocks storage we just ask again next time
    }
    setAgreed(true);
  };

  if (agreed) return children;

  return (
    <div className="app">
      <div className="bg-orbs" aria-hidden="true" />
      <div className="splash">
        <Heartbeat />
        <section className="card consent">
          <h1>Before we check your laptop</h1>
          <p>KAYVAK will read your battery health, drive health, Windows licence and security status.</p>
          <ul>
            <li>Everything stays on this laptop. Nothing is sent to the internet.</li>
            <li>There are no adverts and no payment.</li>
            <li>KAYVAK gives advice only. It does not change or repair anything.</li>
          </ul>
          <button className="btn" onClick={agree}>
            I agree, start the check
          </button>
        </section>
      </div>
    </div>
  );
}

export default ConsentGate;