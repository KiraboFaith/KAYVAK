import { STATUS_STYLES } from '../statusStyles';

function StatusPanel({ status }) {
  const style = STATUS_STYLES[status] || { background: '#777777', color: '#ffffff' };

  return (
    <div style={{ border: '1px solid #ccc', borderRadius: '8px', padding: '16px', minWidth: '140px' }}>
      <p style={{ margin: 0, fontSize: '14px', color: '#888' }}>Overall Health</p>
      <span
        style={{
          display: 'inline-block',
          marginTop: '6px',
          padding: '4px 14px',
          borderRadius: '14px',
          fontSize: '22px',
          fontWeight: 'bold',
          ...style,
        }}
      >
        {status}
      </span>
    </div>
  );
}

export default StatusPanel;