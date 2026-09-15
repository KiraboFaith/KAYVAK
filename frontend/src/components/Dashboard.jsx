import { useState, useEffect } from 'react';
import StatCard from './StatCard';
import StatusPanel from './StatusPanel';
import ActionLog from './ActionLog';

function Dashboard() {
  const [data, setData] = useState(null);

 useEffect(() => {
  const fetchData = () => {
    fetch('http://127.0.0.1:8000/api/sensors/data/')
      .then((res) => res.json())
      .then((json) => setData(json))
      .catch((err) => console.error('Failed to fetch sensor data:', err));
  };

  fetchData(); // initial load
  const interval = setInterval(fetchData, 5000); // poll every 5s

  return () => clearInterval(interval); // cleanup on unmount
}, []);

  if (!data) {
    return <p style={{ padding: '24px' }}>Loading sensor data...</p>;
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', gap: '16px' }}>
        <StatCard label="Temperature" value={data.temperature} unit="°C" />
        <StatCard label="Humidity" value={data.humidity} unit="%" />
        <StatusPanel status={data.status} />
      </div>
      <ActionLog entries={data.log} />
    </div>
  );
}

export default Dashboard;