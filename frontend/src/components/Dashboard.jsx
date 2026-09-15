import StatCard from './StatCard';
import StatusPanel from './StatusPanel';

function Dashboard() {
  return (
    <div style={{ display: 'flex', gap: '16px', padding: '24px' }}>
      <StatCard label="Temperature" value={24} unit="°C" />
      <StatCard label="Humidity" value={58} unit="%" />
      <StatusPanel status="Normal" />
    </div>
  );
}

export default Dashboard;