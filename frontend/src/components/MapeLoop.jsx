const STEPS = [
  { letter: 'M', name: 'Monitor', text: 'Reads your battery and drive health.' },
  { letter: 'A', name: 'Analyse', text: 'Compares the readings with safe limits.' },
  { letter: 'P', name: 'Plan', text: 'Chooses the advice: fix it yourself or see a technician.' },
  { letter: 'E', name: 'Execute', text: 'Shows you the result. It never repairs anything.' },
];

function MapeLoop() {
  return (
    <section className="card mape">
      <div className="section-head">
        <h2>How KAYVAK checks your laptop</h2>
        <span className="tag">MAPE-K loop</span>
      </div>
      <ol className="mape-steps">
        {STEPS.map((step, i) => (
          <li key={step.name} className="mape-step" style={{ animationDelay: `${i * 2}s` }}>
            <span className="mape-letter">{step.letter}</span>
            <strong>{step.name}</strong>
            <span>{step.text}</span>
          </li>
        ))}
      </ol>
      <div className="mape-knowledge">
        <span className="mape-letter">K</span>
        <div>
          <strong>Knowledge</strong>
          <span> Remembers the safe limits and every past reading.</span>
        </div>
      </div>
    </section>
  );
}

export default MapeLoop;