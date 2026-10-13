import { STATUS } from '../statusStyles';

function MeterBar({ label, caption, value, status }) {
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
    </div>
  );
}

export default MeterBar;