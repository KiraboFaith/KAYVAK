import { useEffect, useState } from 'react';
import './SnapshotPanel.css';
import { listSnapshots, takeSnapshot, compareSnapshots } from '../snapshots';

const PART_NAMES = {
  disks: 'Storage drive',
  ram: 'Memory (RAM)',
  battery: 'Battery',
  display: 'Screen',
  windows: 'Windows install',
};
const RESULT_TEXT = { unchanged: 'Unchanged', changed: 'Changed', not_checked: 'Not checked' };
const ITEM_TEXT = { unchanged: 'Same', removed: 'Removed', added: 'Added', changed: 'Changed' };

// The list is newest first. Compare the newest "before" with the first "after" taken after it.
function pickScans(snapshots) {
  const before = snapshots.find((s) => s.label === 'before');
  if (!before) return {};
  const after = snapshots.find((s) => s.label === 'after' && s.id > before.id);
  return { before, after };
}

function when(iso) {
  return new Date(iso).toLocaleString();
}

function SnapshotPanel() {
  const [snapshots, setSnapshots] = useState([]);
  const [busy, setBusy] = useState(null); // "before", "after" or null
  const [error, setError] = useState(null);
  const [loaded, setLoaded] = useState(null); // { beforeId, afterId, data }

  const reload = () =>
    listSnapshots()
      .then((list) => {
        setSnapshots(list);
        setError(null);
      })
      .catch((e) => setError(e.message));

  useEffect(() => {
    reload();
  }, []);

  const { before, after } = pickScans(snapshots);
  const beforeId = before && before.id;
  const afterId = after && after.id;

  useEffect(() => {
    if (!beforeId || !afterId) return;
    compareSnapshots(beforeId, afterId)
      .then((data) => setLoaded({ beforeId, afterId, data }))
      .catch((e) => setError(e.message));
  }, [beforeId, afterId]);

  // Only show a comparison that belongs to the two scans currently picked.
  const comparison =
    loaded && loaded.beforeId === beforeId && loaded.afterId === afterId ? loaded.data : null;

  const scan = async (label) => {
    setBusy(label);
    setError(null);
    try {
      await takeSnapshot(label);
      await reload();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  };

  const latest = (label) => (label === 'before' ? before : after);
  const unread = (snap) => (snap ? snap.unchecked.map((p) => PART_NAMES[p]) : []);

  return (
    <section className="card snap">
      <div className="section-head">
        <h2>Before and after a repair</h2>
        <span className="tag">Evidence</span>
      </div>
      <p className="snap-note">
        Scan the laptop <strong>before</strong> you hand it over, and again when you collect it.
        We compare the two scans, so you can see which parts really changed. Serial numbers are
        never stored, only a short fingerprint of each.
      </p>
      <p className="snap-note">
        For a fair result, scan the same way both times and unplug external screens. Run the
        backend in an administrator terminal so drive serials can be read.
      </p>

      <div className="snap-actions">
        {['before', 'after'].map((label, i) => (
          <button
            key={label}
            className="btn"
            disabled={busy !== null}
            onClick={() => scan(label)}
          >
            {busy === label ? 'Scanning... (about 20 seconds)' : `${i + 1}. Scan ${label} the repair`}
          </button>
        ))}
      </div>

      {error && <p className="banner">{error}</p>}

      <ul className="snap-scans">
        {['before', 'after'].map((label) => {
          const snap = latest(label);
          return (
            <li key={label}>
              <strong>{label === 'before' ? 'Before scan' : 'After scan'}:</strong>{' '}
              {snap ? when(snap.created) : 'not taken yet'}
              {unread(snap).length > 0 && (
                <span className="snap-warn"> Could not read: {unread(snap).join(', ')}.</span>
              )}
            </li>
          );
        })}
      </ul>

      {comparison && (
        <>
          <div className="snap-summary" data-changed={comparison.changed.length > 0}>
            {comparison.changed.length === 0
              ? 'No part changed between the two scans.'
              : `Changed: ${comparison.changed.join(', ')}.`}
          </div>
          <table className="snap-table">
            <thead>
              <tr>
                <th>Part</th>
                <th>Result</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {comparison.components.map((part) => (
                <tr key={part.component}>
                  <td>{part.component}</td>
                  <td>
                    <span className="snap-badge" data-result={part.status}>
                      {RESULT_TEXT[part.status]}
                    </span>
                  </td>
                  <td>
                    <p className="snap-summary-line">{part.summary}</p>
                    {part.items.map((item, i) => (
                      <p key={i} className="snap-item">
                        <span className="snap-badge small" data-result={item.state}>
                          {ITEM_TEXT[item.state]}
                        </span>{' '}
                        {item.label}
                        {item.detail && <small> {item.detail}</small>}
                      </p>
                    ))}
                    {part.notes.map((note) => (
                      <p key={note} className="snap-flag">
                        {note}
                      </p>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="snap-note">{comparison.limits}</p>
        </>
      )}
    </section>
  );
}

export default SnapshotPanel;