function Heartbeat({ small = false }) {
  const d = 'M0 20 H32 L40 6 L50 34 L58 20 H120';
  return (
    <svg className={small ? 'heartbeat small' : 'heartbeat'} viewBox="0 0 120 40" aria-hidden="true">
      <path className="heartbeat-ghost" d={d} />
      <path className="heartbeat-line" d={d} pathLength="1" />
    </svg>
  );
}

export default Heartbeat;