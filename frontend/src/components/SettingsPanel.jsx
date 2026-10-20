import { useState, useEffect } from 'react';
import { getNotificationSetting, saveNotificationSetting } from '../notifications';

// Lets the owner switch urgent alerts on or off at any time.
function SettingsPanel({ onClose }) {
  const [enabled, setEnabled] = useState(null); // null = still loading
  const [error, setError] = useState(null);

  useEffect(() => {
    getNotificationSetting()
      .then((setting) => setEnabled(setting.enabled))
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
    </section>
  );
}

export default SettingsPanel;