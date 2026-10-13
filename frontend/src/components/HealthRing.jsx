const RADIUS = 66;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function HealthRing({ passed, total, status }) {
  const offset = CIRCUMFERENCE * (1 - passed / total);

  return (
    <div
      className="ring"
      data-status={status}
      role="img"
      aria-label={`${passed} of ${total} checks passed`}
    >
      {status !== 'Good' && <span className="ring-pulse" />}
      <svg viewBox="0 0 160 160">
        <circle className="ring-track" cx="80" cy="80" r={RADIUS} />
        <circle
          className="ring-bar"
          cx="80"
          cy="80"
          r={RADIUS}
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          style={{ '--circ': CIRCUMFERENCE }}
        />
      </svg>
      <div className="ring-centre">
        <strong>
          {passed}/{total}
        </strong>
        <span>checks passed</span>
      </div>
    </div>
  );
}

export default HealthRing;