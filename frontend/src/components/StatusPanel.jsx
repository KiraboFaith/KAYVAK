function StatusPanel({ status }) {
  const colors = {
    Normal: '#4CAF50',
    Warning: '#FF9800',
    Alert: '#F44336',
  };

  return (
    <div style={{ border: '1px solid #ccc', borderRadius: '8px', padding: '16px', minWidth: '140px' }}>
      <p style={{ margin: 0, fontSize: '14px', color: '#888' }}>System Status</p>
      <p style={{ margin: 0, fontSize: '24px', fontWeight: 'bold', color: colors[status] || '#000' }}>
        {status}
      </p>
    </div>
  );
}

export default StatusPanel;