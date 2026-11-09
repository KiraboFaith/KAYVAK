// Talks to the backend about before/after hardware snapshots.
import { apiFetch } from './api';

const BASE = 'http://127.0.0.1:8000/api/sensors/snapshots/';

async function readJson(res, fallback) {
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || fallback);
  return body;
}

export async function listSnapshots() {
  return readJson(await apiFetch(BASE), 'Cannot read the saved scans');
}

// label is "before" or "after". The scan takes a while (about 20 seconds).
export async function takeSnapshot(label) {
  const res = await apiFetch(BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label }),
  });
  return readJson(res, 'Cannot take the scan');
}

export async function compareSnapshots(beforeId, afterId) {
  const res = await apiFetch(`${BASE}compare/?before=${beforeId}&after=${afterId}`);
  return readJson(res, 'Cannot compare the scans');
}