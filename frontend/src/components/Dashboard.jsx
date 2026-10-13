import { useState, useEffect } from 'react';
import { STATUS, statusOf } from '../statusStyles';
import Heartbeat from './Heartbeat';
import HealthRing from './HealthRing';
import MeterBar from './MeterBar';
import FindingCard from './FindingCard';
import MapeLoop from './MapeLoop';
import PrintReport from './PrintReport';

const API_URL = 'http://127.0.0.1:8000/api/sensors/health/';
const TOTAL_CHECKS = 4; // battery, drive, licence, security

function Dashboard() {
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);

  useEffect(() => {
    const fetchReport = () => {
      fetch(API_URL)
        .then((res) => {
          if (!res.ok) throw new Error('No data yet');
          return res.json();
        })
        .then((json) => {
          setReport(json);
          setError(null);
          setUpdatedAt(new Date());
        })
        .catch(() => setError('Cannot get the health report. Is the backend running?'));
    };

    fetchReport();
    const interval = setInterval(fetchReport, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!report) {
    return (
      <div className="app">
        <div className="bg-orbs" aria-hidden="true" />
        <div className="splash">
          <Heartbeat />
          <p>{error || 'Checking your laptop...'}</p>
        </div>
      </div>
    );
  }

  const info = STATUS[report.overall];
  const passed = Math.max(0, TOTAL_CHECKS - report.findings.length);

  return (
    <div className="app">
      <div className="bg-orbs" aria-hidden="true" />

      <div className="screen-only">
        <header className="topbar">
          <div className="brand">
            <Heartbeat small />
            <div>
              <strong>KAYVAK</strong>
              <span>Laptop Health Check</span>
            </div>
          </div>
          <div className="topbar-actions">
            <span className="live">
              <i className="dot" />
              Demo data · {updatedAt ? updatedAt.toLocaleTimeString() : ''}
            </span>
            <button className="btn" onClick={() => window.print()}>
              🖨 Print report
            </button>
          </div>
        </header>

        {error && <p className="banner">{error}</p>}

        <section className="card hero" data-status={report.overall}>
          <HealthRing passed={passed} total={TOTAL_CHECKS} status={report.overall} />
          <div className="hero-text">
            <span className="chip" data-status={report.overall}>
              <span aria-hidden="true">{info.icon}</span> {report.overall}
            </span>
            <h1>{info.headline}</h1>
            <p>{info.message}</p>
          </div>
        </section>

        <section className="meters">
          <MeterBar
            label="Battery health"
            caption="of original capacity"
            value={report.measurements.battery_health}
            status={statusOf(report, 'Battery')}
          />
          <MeterBar
            label="Drive health"
            caption="of drive life left"
            value={report.measurements.drive_health}
            status={statusOf(report, 'Storage drive')}
          />
        </section>

        <section>
          <div className="section-head">
            <h2>What we found</h2>
            <span className="tag">
              {report.findings.length === 0
                ? 'No problems'
                : `${report.findings.length} ${report.findings.length === 1 ? 'problem' : 'problems'}`}
            </span>
          </div>

          {report.findings.length === 0 ? (
            <div className="card all-good" data-status="Good">
              <span className="all-good-icon">✓</span>
              <h3>No problems found</h3>
              <p>Your laptop looks healthy. We will keep checking.</p>
            </div>
          ) : (
            <div className="findings-grid">
              {report.findings.map((finding, i) => (
                <FindingCard key={finding.component} finding={finding} index={i} />
              ))}
            </div>
          )}
        </section>

        <MapeLoop />

        <footer className="footer">
          KAYVAK gives advice only. It does not replace a technician. Readings in this version are
          simulated.
        </footer>
      </div>

      <PrintReport report={report} />
    </div>
  );
}

export default Dashboard;