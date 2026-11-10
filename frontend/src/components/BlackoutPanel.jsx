import { useState, useEffect } from 'react';
import { apiFetch } from '../api';

const URL = 'http://127.0.0.1:8000/api/sensors/blackouts/';

// Shows what KAYVAK found about the most recent unexpected shutdown.
function BlackoutPanel() {
  const [latest, setLatest] = useState(null);

  useEffect(() => {
    const load = () => {
      apiFetch(URL)
        .then((res) => (res.ok ? res.json() : []))
        .then((list) => setLatest(list.length > 0 ? list[0] : null))
        .catch(() => setLatest(null));
    };
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  if (!latest) return null;

  return (
    <section className="card" aria-label="Last unexpected shutdown">
      <div className="section-head">
        <h2>Last unexpected shutdown</h2>
        <span className="tag">{new Date(latest.event_time).toLocaleString()}</span>
      </div>
      <p style={{ whiteSpace: 'pre-wrap' }}>{latest.summary}</p>
    </section>
  );
}

export default BlackoutPanel;