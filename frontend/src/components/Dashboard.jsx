import { STATUS } from '../statusStyles';

// Turns the backend trend into one plain sentence for a non-technical reader.
function trendText(trend) {
  if (!trend) return 'Collecting readings to spot a trend...';
  if (trend.checks_to_critical === 0) return 'Already in the critical range.';
  if (trend.direction === 'falling') {
    const next =
      trend.checks_to_warning === 0
        ? `about ${trend.checks_to_critical} checks from critical`
        : `about ${trend.checks_to_warning} checks from a warning`;
    return `Falling ${Math.abs(trend.change_per_check)} points per check, ${next}.`;
  }
  return trend.direction === 'rising' ? 'Improving.' : 'Holding steady.';
}

function MeterBar({ label, caption, value, status, trend, fallback }) {
  // No number from Windows. If Windows still gave a real answer (fallback, for example
  // "Healthy"), show that. Otherwise say so instead of showing a made-up number.
  if (value === null || value === undefined) {
    if (fallback) {
      return (
        <div className="card meter" data-status={status}>
          <div className="meter-top">
            <span className="meter-label">{label}</span>
            <span className="chip small" data-status={status}>
              <span aria-hidden="true">{STATUS[status].icon}</span> {status}
            </span>
          </div>
          <div className="meter-value">{fallback.value}</div>
          <span className="meter-caption">{fallback.caption}</span>
        </div>
      );
    }
    return (
      <div className="card meter">
        <div className="meter-top">
          <span className="meter-label">{label}</span>
        </div>
        <div className="meter-value">
          <small>Not measured</small>
        </div>
        <span className="meter-caption">
          Windows gives no single health score for this drive. See the measurements below.
        </span>
      </div>
    );
  }
  const percent = Math.max(0, Math.min(100, value));

  return (
    <div className="card meter" data-status={status}>
      <div className="meter-top">
        <span className="meter-label">{label}</span>
        <span className="chip small" data-status={status}>
          <span aria-hidden="true">{STATUS[status].icon}</span> {status}
        </span>
      </div>
      <div className="meter-value">
        {Number(value).toFixed(1)}
        <small>%</small>
      </div>
      <div
        className="meter-track"
        role="progressbar"
        aria-valuenow={Math.round(percent)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <div className="meter-fill" style={{ width: `${percent}%` }} />
      </div>
      <span className="meter-caption">{caption}</span>
      <span className="meter-trend" data-direction={trend ? trend.direction : 'none'}>
        {trendText(trend)}
      </span>
    </div>
  );
}

export default MeterBar;