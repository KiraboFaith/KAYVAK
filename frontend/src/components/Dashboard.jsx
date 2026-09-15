import StatCard from './StatCard';

function Dashboard() {
  return (
    <div style={{ display: 'flex', gap: '16px', padding: '24px' }}>
      <StatCard label="Temperature" value={24} unit="°C" />
      <StatCard label="Humidity" value={58} unit="%" />
    </div>
  );
}

export default Dashboard;