// Every request to the backend goes through here so it carries the header
// the backend requires (see backend/sensors/permissions.py).
export function apiFetch(url, options = {}) {
  return fetch(url, {
    ...options,
    headers: { ...options.headers, 'X-Kayvak-Client': 'dashboard' },
  });
}