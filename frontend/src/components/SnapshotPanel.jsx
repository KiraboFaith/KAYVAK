import './SnapshotPanel.css';

const PART_NAMES = {
  disks: 'Storage drive',
  ram: 'Memory (RAM)',
  battery: 'Battery',
  display: 'Screen',
  windows: 'Windows install',
};
const RESULT_TEXT = { unchanged: 'Unchanged', changed: 'Changed', not_checked: 'Not checked' };
const ITEM_TEXT = { unchanged: 'Same', removed: 'Removed', added: 'Added', changed: 'Changed' };

function when(iso) {
  return new Date(iso).toLocaleString();
}

// What one scan found, part by part.
function ScanResults({ detail }) {
  if (!detail) return <p className="snap-note">Loading what the scan found...</p>;
  return (
    <table className="snap-table">
      <thead>
        <tr>
          <th>Part</th>
          <th>What the scan found</th>
        </tr>
      </thead>
      <tbody>
        {detail.components.map((part) => (
          <tr key={part.component}>
            <td>{part.component}</td>
            <td>
              {part.status === 'not_checked' && (
                <p className="snap-flag">Could not be read in this scan.</p>
              )}
              {part.status === 'read' && part.items.length === 0 && (
                <p className="snap-item">Nothing found.</p>
              )}
              {part.items.map((item, i) => (
                <p key={i} className="snap-item">
                  {item.label}
                  {item.detail && <small> {item.detail}</small>}
                </p>
              ))}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SnapshotPanel({ scans }) {
  const { before, after, beforeDetail, afterDetail, comparison, busy, error, scan } = scans;

  const latest = (label) => (label === 'before' ? before : after);
  const detailOf = (label) => (label === 'before' ? beforeDetail : afterDetail);
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

      {error && <p className="banner">{error}</p>}

      {['before', 'after'].map((label, i) => {
        const snap = latest(label);
        return (
          <div className="snap-step" key={label}>
            <div className="snap-actions">
              <button
                className="btn"
                disabled={busy !== null || (label === 'after' && !before)}
                onClick={() => scan(label)}
              >
                {busy === label
                  ? 'Scanning...'
                  : `${i + 1}. Scan ${label} the repair`}
              </button>
            </div>
            <p className="snap-scans">
              <strong>{label === 'before' ? 'Before scan' : 'After scan'}:</strong>{' '}
              {snap ? when(snap.created) : label === 'after' && !before ? 'take the before scan first' : 'not taken yet'}
              {unread(snap).length > 0 && (
                <span className="snap-warn"> Could not read: {unread(snap).join(', ')}.</span>
              )}
            </p>
            {snap && <ScanResults detail={detailOf(label)} />}
          </div>
        );
      })}

      {comparison && (
        <>
          <h3 className="snap-heading">3. Comparison</h3>
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