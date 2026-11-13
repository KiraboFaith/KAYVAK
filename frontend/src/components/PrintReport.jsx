import { statusOf } from '../statusStyles';
import { getCareTips } from '../careTips';

const RESULT_TEXT = { unchanged: 'Unchanged', changed: 'Changed', not_checked: 'Not checked' };
const ITEM_TEXT = { unchanged: 'Same', removed: 'Removed', added: 'Added', changed: 'Changed' };

// What one scan found, for the printed page.
function ScanTable({ title, snap, detail }) {
  return (
    <>
      <h3>
        {title}
        {snap ? `: ${new Date(snap.created).toLocaleString()}` : ': not taken'}
      </h3>
      {snap && !detail && <p>Loading what the scan found...</p>}
      {detail && (
        <table>
          <thead>
            <tr>
              <th>Part</th>
              <th>What the scan found</th>
            </tr>
          </thead>
          <tbody>
            {detail.components.map((part) => (
              <tr key={part.component}>
                <td>{part.component}</td>
                <td>
                  {part.status === 'not_checked' && 'Could not be read in this scan.'}
                  {part.status === 'read' && part.items.length === 0 && 'Nothing found.'}
                  {part.items.map((item, i) => (
                    <div key={i}>
                      {item.label}
                      {item.detail && ` ${item.detail}`}
                    </div>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

// The before and after scans and what changed between them (empty until a scan is taken).
function RepairEvidence({ scans }) {
  const { before, after, beforeDetail, afterDetail, comparison } = scans;
  return (
    <>
      <h2>Before and after a repair</h2>
      {!before && <p>No scan has been taken, so there is no repair evidence yet.</p>}
      {before && (
        <ScanTable title="Before scan" snap={before} detail={beforeDetail} />
      )}
      {before && !after && <p>The after scan has not been taken yet.</p>}
      {after && <ScanTable title="After scan" snap={after} detail={afterDetail} />}
      {comparison && (
        <>
          <h3>Comparison</h3>
          <p>
            <strong>
              {comparison.changed.length === 0
                ? 'No part changed between the two scans.'
                : `Changed: ${comparison.changed.join(', ')}.`}
            </strong>
          </p>
          <table>
            <thead>
              <tr>
                <th>Part</th>
                <th>Result</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {comparison.components.map((part) => (
                <tr key={part.component}>
                  <td>{part.component}</td>
                  <td>{RESULT_TEXT[part.status]}</td>
                  <td>
                    <div>{part.summary}</div>
                    {part.items.map((item, i) => (
                      <div key={i}>
                        {ITEM_TEXT[item.state]}: {item.label}
                        {item.detail && ` ${item.detail}`}
                      </div>
                    ))}
                    {part.notes.map((note) => (
                      <div key={note}>
                        <strong>{note}</strong>
                      </div>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p>{comparison.limits}</p>
        </>
      )}
    </>
  );
}

// FR-10: a printable report a technician can use to verify the findings.
// It is hidden on screen and only appears when the page is printed.
function PrintReport({ report, scans }) {
  const printed = new Date().toLocaleString();
  const taken = new Date(report.timestamp).toLocaleString();
  const licenceStatus = statusOf(report, 'Windows licence');
  const securityStatus = statusOf(report, 'Security');
  const unchecked = report.unchecked || [];
  const rows = [
    {
      check: 'Battery health',
      value: `${report.measurements.battery_health}% of original capacity`,
      result: statusOf(report, 'Battery'),
    },
    {
      check: 'Storage drive health',
      value: unchecked.includes('Storage drive')
        ? 'Not measured (Windows does not report it for this drive)'
        : `${report.measurements.drive_health}% of drive life left`,
      result: unchecked.includes('Storage drive') ? 'Not checked' : statusOf(report, 'Storage drive'),
    },
    {
      check: 'Windows licence',
      value: unchecked.includes('Windows licence')
        ? 'Not checked'
        : licenceStatus === 'Good' ? 'Check passed' : 'Check failed',
      result: unchecked.includes('Windows licence') ? 'Not checked' : licenceStatus,
    },
    {
      check: 'Security (malware)',
      value: unchecked.includes('Security')
        ? 'Not checked'
        : securityStatus === 'Good' ? 'Nothing suspicious' : 'Suspicious activity',
      result: unchecked.includes('Security') ? 'Not checked' : securityStatus,
    },
  ];

  return (
    <section className="print-only report">
      <h1>KAYVAK Laptop Health Report</h1>
      <p className="report-meta">
        Printed: {printed} | Reading taken: {taken}
      </p>
      <p className="report-meta">
        {report.source === 'simulated'
          ? 'Note: this reading is simulated demo data.'
          : 'Reading taken from this laptop by the KAYVAK Windows collector.'}
      </p>
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
              <strong>Repair size:</strong> {f.repair}. {f.repair_note}
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

      <RepairEvidence scans={scans} />

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