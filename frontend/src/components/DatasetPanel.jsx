import { useEffect, useState } from 'react';

const API_URL = 'http://127.0.0.1:8000/api/sensors/dataset/';

function formatNumber(value) {
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 });
}

// Compares this laptop's disk numbers with real drives from the Backblaze dataset.
function DatasetPanel() {
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch(API_URL)
      .then((res) => {
        if (!res.ok) throw new Error('No dataset summary yet');
        return res.json();
      })
      .then(setData)
      .catch(() => setFailed(true));
  }, []);

  if (failed) {
    return (
      <section className="card dataset">
        <div className="section-head">
          <h2>How your drive compares with real drives</h2>
          <span className="tag">Dataset</span>
        </div>
        <p className="dataset-note">Dataset comparison is not available yet.</p>
      </section>
    );
  }
  if (!data) return null;

  const { dataset, drives } = data;
  return (
    <section className="card dataset">
      <div className="section-head">
        <h2>How your drive compares with real drives</h2>
        <span className="tag">Dataset</span>
      </div>
      <p className="dataset-note">
        Your numbers come from this laptop. The comparison drives come from the{' '}
        <strong>{dataset.source}</strong> dataset ({dataset.models.join(', ')},{' '}
        {dataset.date_from} to {dataset.date_to}): {formatNumber(dataset.healthy_drives)} drives
        that kept working and {formatNumber(dataset.failed_drives)} that failed.
      </p>

      {drives.length === 0 && (
        <p className="dataset-note">No disk numbers have been collected from this laptop yet.</p>
      )}

      {drives.map((drive) => (
        <div key={drive.device_id} className="dataset-drive">
          <h3>
            {drive.name} <small>({drive.media_type || 'unknown type'})</small>
          </h3>
          {drive.note && <p className="dataset-note">{drive.note}</p>}
          {drive.metrics.length > 0 && (
            <table className="dataset-table">
              <thead>
                <tr>
                  <th>Number</th>
                  <th>Your drive</th>
                  <th>Typical drive that kept working</th>
                  <th>Typical drive that failed</th>
                  <th>Where you sit</th>
                </tr>
              </thead>
              <tbody>
                {drive.metrics.map((metric) => (
                  <tr key={metric.key}>
                    <td>{metric.label}</td>
                    <td>{formatNumber(metric.value)}</td>
                    <td>{formatNumber(metric.healthy_median)}</td>
                    <td>
                      {metric.failed_median === null ? '-' : formatNumber(metric.failed_median)}
                    </td>
                    <td>
                      {metric.outside_range
                        ? metric.percentile === 100
                          ? 'Higher than every drive in the dataset'
                          : 'Lower than every drive in the dataset'
                        : `Higher than ${Math.round(metric.percentile)}% of the dataset drives`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ))}

      <p className="dataset-caution">{data.caution}</p>
    </section>
  );
}

export default DatasetPanel;