import { STATUS_STYLES } from '../statusStyles';

function FindingCard({ finding }) {
  const style = STATUS_STYLES[finding.status] || { background: '#777777', color: '#ffffff' };

  return (
    <div
      style={{
        border: '1px solid #ccc',
        borderLeft: `8px solid ${style.background}`,
        borderRadius: '8px',
        padding: '16px',
        marginTop: '16px',
        maxWidth: '600px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        <strong style={{ fontSize: '18px' }}>{finding.component}</strong>
        <span style={{ padding: '2px 10px', borderRadius: '12px', fontSize: '13px', fontWeight: 'bold', ...style }}>
          {finding.status}
        </span>
        <span style={{ fontSize: '13px', color: '#888' }}>
          {finding.type === 'hardware' ? 'Hardware problem' : 'Software problem'}
        </span>
      </div>

      <p style={{ margin: '10px 0 6px 0' }}>{finding.explanation}</p>
      <p style={{ margin: '0 0 6px 0' }}>
        <strong>Proof:</strong> {finding.evidence}
      </p>
      <p style={{ margin: 0 }}>
        <strong>What to do:</strong> {finding.advice}
      </p>
    </div>
  );
}

export default FindingCard;