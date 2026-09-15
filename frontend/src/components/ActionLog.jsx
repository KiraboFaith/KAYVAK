function ActionLog({ entries }) {
  return (
    <div style={{ border: '1px solid #ccc', borderRadius: '8px', padding: '16px', marginTop: '16px', maxWidth: '500px' }}>
      <p style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#888' }}>Decision & Action Log</p>
      <ul style={{ margin: 0, paddingLeft: '20px' }}>
        {entries.map((entry, index) => (
          <li key={index} style={{ marginBottom: '6px' }}>{entry}</li>
        ))}
      </ul>
    </div>
  );
}

export default ActionLog;