import { statusOf } from '../statusStyles';
import { getCareTips } from '../careTips';

// FR-10: a printable report a technician can use to verify the findings.
// It is hidden on screen and only appears when the page is printed.
function PrintReport({ report }) {
  const printed = new Date().toLocaleString();
  const taken = new Date(report.timestamp).toLocaleString();
  const licenceStatus = statusOf(report, 'Windows licence');
  const securityStatus = statusOf(report, 'Security');

  const rows = [
    {
      check: 'Battery health',
      value: `${report.measurements.battery_health}% of original capacity`,
      result: statusOf(report, 'Battery'),
    },
    {
      check: 'Storage drive health',
      value: `${report.measurements.drive_health}% of drive life left`,
      result: statusOf(report, 'Storage drive'),
    },
    {
      check: 'Windows licence',
      value: licenceStatus === 'Good' ? 'Check passed' : 'Check failed',
      result: licenceStatus,
    },
    {
      check: 'Security (malware)',
      value: securityStatus === 'Good' ? 'Nothing suspicious' : 'Suspicious activity',
      result: securityStatus,
    },
  ];

  return (
    <section className="print-only report">
      <h1>KAYVAK Laptop Health Report</h1>
      <p className="report-meta">
        Printed: {printed} | Reading taken: {taken}
      </p>
      <p className="report-meta">Note: this version uses simulated demo readings.</p>

      <h2>Overall result: {report.overall}</h2>

      <table>
        <thead>
          <tr>
            <th>Check</th>
            <th>Measured value</th>
            <th>Result</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.check}>
              <td>{row.check}</td>
              <td>{row.value}</td>
              <td>{row.result}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Problems found</h2>
      {report.findings.length === 0 ? (
        <p>No problems were found.</p>
      ) : (
        report.findings.map((f) => (
          <div className="report-finding" key={f.component}>
            <h3>
              {f.component}: {f.status} ({f.type === 'hardware' ? 'hardware' : 'software'} problem)
            </h3>
            <p>
              <strong>What it means:</strong> {f.explanation}
            </p>
            <p>
              <strong>Proof:</strong> {f.evidence}
            </p>
            <p>
              <strong>What to do:</strong> {f.advice}
            </p>
            {getCareTips(f.component).length > 0 && (
              <ul>
                {getCareTips(f.component).map((tip) => (
                  <li key={tip}>{tip}</li>
                ))}
              </ul>
            )}
          </div>
        ))
      )}

      <div className="report-sign">
        <p>
          <strong>Technician&apos;s comments:</strong>
        </p>
        <div className="report-line" />
        <div className="report-line" />
        <p>Technician name and signature: ______________________________</p>
      </div>

      <p className="report-foot">
        This report is advice only. It does not replace a technician&apos;s judgement. Please ask a
        technician to confirm the results.
      </p>
    </section>
  );
}

export default PrintReport;