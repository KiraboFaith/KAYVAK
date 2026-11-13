// Keeps the before/after scans in one place, so the scan panel and the printed report
// show the same thing. The list is newest first.
import { useCallback, useEffect, useState } from 'react';
import { listSnapshots, takeSnapshot, getSnapshot, compareSnapshots } from './snapshots';

// Newest "before", and the newest "after" taken after it.
function pickScans(snapshots) {
  const before = snapshots.find((s) => s.label === 'before');
  if (!before) return {};
  const after = snapshots.find((s) => s.label === 'after' && s.id > before.id);
  return { before, after };
}

// Holds a fetched result together with the id it belongs to, so an old result
// is never shown for a newer scan.
function useById(id, fetcher, onError) {
  const [loaded, setLoaded] = useState(null); // { id, data }
  useEffect(() => {
    if (!id) return;
    fetcher(id)
      .then((data) => setLoaded({ id, data }))
      .catch((e) => onError(e.message));
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
  return loaded && loaded.id === id ? loaded.data : null;
}

export function useScans() {
  const [snapshots, setSnapshots] = useState([]);
  const [busy, setBusy] = useState(null); // "before", "after" or null
  const [error, setError] = useState(null);

  const reload = useCallback(
    () =>
      listSnapshots()
        .then((list) => {
          setSnapshots(list);
          setError(null);
        })
        .catch((e) => setError(e.message)),
    [],
  );

  useEffect(() => {
    reload();
  }, [reload]);

  const { before, after } = pickScans(snapshots);
  const beforeId = before && before.id;
  const afterId = after && after.id;

  const beforeDetail = useById(beforeId, getSnapshot, setError);
  const afterDetail = useById(afterId, getSnapshot, setError);

  const [comparisonLoaded, setComparisonLoaded] = useState(null);
  useEffect(() => {
    if (!beforeId || !afterId) return;
    compareSnapshots(beforeId, afterId)
      .then((data) => setComparisonLoaded({ beforeId, afterId, data }))
      .catch((e) => setError(e.message));
  }, [beforeId, afterId]);
  const comparison =
    comparisonLoaded && comparisonLoaded.beforeId === beforeId && comparisonLoaded.afterId === afterId
      ? comparisonLoaded.data
      : null;

  const scan = async (label) => {
    setBusy(label);
    setError(null);
    try {
      await takeSnapshot(label);
      await reload();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  };

  return { before, after, beforeDetail, afterDetail, comparison, busy, error, scan };
}