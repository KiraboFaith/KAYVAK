const show = (value, unit = '') =>
  value === null || value === undefined ? 'Not reported' : `${value}${unit}`;

function timeInUse(hours) {
  if (hours === null || hours === undefined) return 'Not reported';
  return `${hours} hours (about ${Math.round(hours / 24)} days)`;
}

function wearText(drive) {
  if (drive.media_type === 'HDD') return 'Hard drives cannot report this';
  if (drive.wear === null || drive.wear === undefined) return 'Not reported';
  return `${drive.wear}% used`;
}

function DriveDetails({ drives }) {
  if (!drives || drives.length === 0) return null;

  return (
    <section>
      <div className="section-head">
        <h2>Drive measurements</h2>
        <span className="tag">
          {drives.length} {drives.length === 1 ? 'drive' : 'drives'}
        </span>
      </div>
      <div className="drives-grid">
        {drives.map((drive, i) => (
          <div className="card drive-card" key={`${drive.name}-${i}`}>
            <h3>{drive.name}</h3>
            <span className="tag">{drive.media_type || 'Unknown type'}</span>
            <dl>
              <div><dt>Windows says</dt><dd>{show(drive.health_status)}</dd></div>
              <div><dt>Temperature</dt><dd>{show(drive.temperature, ' °C')}</dd></div>
              <div><dt>Time in use</dt><dd>{timeInUse(drive.power_on_hours)}</dd></div>
              <div><dt>Wear</dt><dd>{wearText(drive)}</dd></div>
              <div><dt>Unfixable read errors</dt><dd>{show(drive.read_errors_uncorrected)}</dd></div>
            </dl>
          </div>
        ))}
      </div>
    </section>
  );
}

export default DriveDetails;