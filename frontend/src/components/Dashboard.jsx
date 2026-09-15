import StatCard from './StatCard';
import StatusPanel from './StatusPanel';
import ActionLog from './ActionLog';

function Dashboard() {
  const mockLog = [
    'Monitored: Temp 24°C, Humidity 58% — within normal range',
    'Analyzed: No anomaly detected',
    'Planned: No action needed',
    'Executed: System idle',
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', gap: '16px' }}>
        <StatCard label="Temperature" value={24} unit="°C" />
        <StatCard label="Humidity" value={58} unit="%" />
        <StatusPanel status="Normal" />
      </div>
      <ActionLog entries={mockLog} />
    </div>
  );
}

export default Dashboard;