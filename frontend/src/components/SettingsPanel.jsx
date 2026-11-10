import { useState, useEffect } from 'react';
import { getNotificationSetting, saveNotificationSetting, saveEmailSetting } from '../notifications';

// Lets the owner switch urgent alerts and email alerts on or off at any time.
function SettingsPanel({ onClose }) {
  const [enabled, setEnabled] = useState(null); // null = still loading
  const [emailEnabled, setEmailEnabled] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getNotificationSetting()
      .then((setting) => {
        setEnabled(setting.enabled);
        setEmailEnabled(setting.email_enabled);
      })
      .catch(() => setError('Could not read your settings. Is the backend running?'));
  }, []);

  const toggle = (event) => {
    const next = event.target.checked;
    saveNotificationSetting(next)
      .then((setting) => {
        setEnabled(setting.enabled);
        setError(null);
      })
      .catch(() => setError('Could not save your choice. Is the backend running?'));
  };

  const toggleEmail = (event) => {
    const next = event.target.checked;
    saveEmailSetting(next)
      .then((setting) => {
        setEmailEnabled(setting.email_enabled);
        setError(null);
      })
      .catch(() => setError('Could not save your choice. Is the backend running?'));
  };

  return (
    <section className="card settings" aria-label="Settings">
      <div className="section-head">
        <h2>Settings</h2>
        <button className="btn btn-quiet" onClick={onClose}>
          Close
        </button>
      </div>
      {error && <p className="banner">{error}</p>}
      <label className="settings-row">
        <input type="checkbox" checked={enabled === true} disabled={enabled === null} onChange={toggle} />
        <span>
          <strong>Urgent alerts</strong>
          <small>
            Show a pop-up on this laptop when a serious (Critical) problem is found. Works while
            the KAYVAK check is running.
          </small>
        </span>
      </label>
      <label className="settings-row">
        <input
          type="checkbox"
          checked={emailEnabled === true}
          disabled={emailEnabled === null}
          onChange={toggleEmail}
        />
        <span>
          <strong>Alerts by email (to your phone)</strong>
          <small>
            Email you about urgent problems, a low battery, and what Windows recorded after an
            unexpected shutdown. If you also set up the optional online signal, KAYVAK sends a
            small &quot;I am alive&quot; message (laptop name and battery charge) to your own
            server. Nothing is sent unless this is on.
          </small>
        </span>
      </label>
    </section>
  );
}

export default SettingsPanel;