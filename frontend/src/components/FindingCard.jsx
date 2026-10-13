import { STATUS } from '../statusStyles';
import { getCareTips } from '../careTips';

const ICONS = {
  Battery: '🔋',
  'Storage drive': '💾',
  'Windows licence': '🔑',
  Security: '🛡️',
};

function FindingCard({ finding, index }) {
  const tips = getCareTips(finding.component);

  return (
    <article
      className="card finding"
      data-status={finding.status}
      style={{ animationDelay: `${index * 120}ms` }}
    >
      <div className="finding-head">
        <span className="finding-icon" aria-hidden="true">
          {ICONS[finding.component] || '⚙️'}
        </span>
        <div className="finding-title">
          <h3>{finding.component}</h3>
          <span className="tag">
            {finding.type === 'hardware' ? 'Hardware problem' : 'Software problem'}
          </span>
        </div>
        <span className="chip" data-status={finding.status}>
          <span aria-hidden="true">{STATUS[finding.status].icon}</span> {finding.status}
        </span>
      </div>

      <p className="finding-explain">{finding.explanation}</p>

      <div className="proof">
        <span className="proof-label">Proof</span>
        <span className="proof-text">{finding.evidence}</span>
      </div>

      <div className="todo">
        <span className="todo-label">What to do</span>
        <p>{finding.advice}</p>
      </div>

      {tips.length > 0 && (
        <details className="care">
          <summary>Care tips</summary>
          <ul>
            {tips.map((tip) => (
              <li key={tip}>{tip}</li>
            ))}
          </ul>
        </details>
      )}
    </article>
  );
}

export default FindingCard;