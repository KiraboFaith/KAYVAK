// Talks to the backend about the owner's notification choice.
const URL = 'http://127.0.0.1:8000/api/sensors/notifications/';

export async function getNotificationSetting() {
  const res = await fetch(URL);
  if (!res.ok) throw new Error('Cannot read notification setting');
  return res.json(); // { enabled, asked }
}

export async function saveNotificationSetting(enabled) {
  const res = await fetch(URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error('Cannot save notification setting');
  return res.json();
}