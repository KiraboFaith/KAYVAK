import { useState, useEffect } from 'react';
import StatCard from './StatCard';
import StatusPanel from './StatusPanel';
import FindingCard from './FindingCard';

function Dashboard() {
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchReport = () => {
      fetch('http://127.0.0.1:8000/api/sensors/health/')
        .then((res) => {
          if (!res.ok) throw new Error('No data yet');
          return res.json();
        })
        .then((json) => {
          setReport(json);
          setError(null);
        })
        .catch(() => setError('Cannot get the health report. Is the backend running?'));
    };

    fetchReport();
    const interval = setInterval(fetchReport, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!report) {
    return <p style={{ padding: '24px' }}>{error || 'Checking your laptop...'}</p>;
  }

  return (
    <div style={{ padding: '24px' }}>
      <h2 style={{ marginTop: 0 }}>Laptop Health Check</h2>
      {error && <p style={{ color: '#C62828' }}>{error}</p>}

      <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
        <StatusPanel status={report.overall} />
        <StatCard label="Battery health" value={report.measurements.battery_health} unit="%" />
        <StatCard label="Drive health" value={report.measurements.drive_health} unit="%" />
      </div>

      {report.findings.length === 0 ? (
        <p style={{ marginTop: '16px' }}>No problems found. Your laptop looks healthy.</p>
      ) : (
        report.findings.map((finding) => (
          <FindingCard key={finding.component} finding={finding} />
        ))
      )}
    </div>
  );
}

export default Dashboard;