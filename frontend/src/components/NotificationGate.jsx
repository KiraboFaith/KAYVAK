import { useState, useEffect } from 'react';
import Heartbeat from './Heartbeat';
import { getNotificationSetting, saveNotificationSetting } from '../notifications';

// The first time the app opens, ask if the owner wants urgent alerts.
// Either answer is saved, so we do not ask again. They can change it later in Settings.
function NotificationGate({ children }) {
  const [state, setState] = useState('loading'); // loading | ask | done
  const [error, setError] = useState(null);

  useEffect(() => {
    getNotificationSetting()
      .then((setting) => setState(setting.asked ? 'done' : 'ask'))
      .catch(() => setState('done')); // backend not ready: do not block the dashboard
  }, []);

  const answer = (enabled) => {
    saveNotificationSetting(enabled)
      .then(() => setState('done'))
      .catch(() => setError('Could not save your choice. Is the backend running?'));
  };

  if (state === 'done') return children;
  if (state === 'loading') return null;

  return (
    <div className="app">
      <div className="bg-orbs" aria-hidden="true" />
      <div className="splash">
        <Heartbeat />
        <section className="card consent">
          <h1>Do you want urgent alerts?</h1>
          <p>
            If your laptop has a serious problem, KAYVAK can show a pop-up on your screen. You
            will not need to open the app to find out.
          </p>
          <ul>
            <li>Only serious (Critical) problems send an alert.</li>
            <li>The pop-up appears on this laptop only. Nothing is sent to the internet.</li>
            <li>You can change this later in Settings.</li>
          </ul>
          {error && <p className="banner">{error}</p>}
          <div className="choice-row">
            <button className="btn" onClick={() => answer(true)}>
              Yes, alert me
            </button>
            <button className="btn btn-quiet" onClick={() => answer(false)}>
              Not now
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}

export default NotificationGate;