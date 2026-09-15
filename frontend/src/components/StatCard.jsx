function StatCard({ label, value, unit }) {
  return (
    <div style={{ border: '1px solid #ccc', borderRadius: '8px', padding: '16px', minWidth: '140px' }}>
      <p style={{ margin: 0, fontSize: '14px', color: '#888' }}>{label}</p>
      <p style={{ margin: 0, fontSize: '28px', fontWeight: 'bold' }}>{value}{unit}</p>
    </div>
  );
}

export default StatCard;