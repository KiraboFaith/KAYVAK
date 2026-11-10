"""Reads Windows' own record of bad shutdowns (the System event log).

- Event 41  (Kernel-Power): Windows restarted without a clean shutdown. Has a stop code,
            which is 0 when Windows did not crash (power cut, hard reset, battery flat).
- Event 6008 (EventLog): "the previous shutdown was unexpected".
- Event 1001 (WER-SystemErrorReporting): Windows crashed (blue screen). Message has the code.

IMPORTANT: Windows writes these when it starts again, so the event time is the time of the
RESTART, not the moment the power was lost.
"""
import json
import re
import subprocess
from datetime import datetime, timedelta

EVENT_SCRIPT = (
    "$events = @(Get-WinEvent -FilterHashtable @{LogName='System'; Id=41,6008,1001; "
    "StartTime=(Get-Date).AddDays(-DAYS)} -ErrorAction SilentlyContinue | "
    "Select-Object @{n='Time';e={$_.TimeCreated.ToString('yyyy-MM-dd HH:mm:sszzz')}}, "
    "Id, ProviderName, "
    "@{n='Bugcheck';e={ if ($_.Id -eq 41) { $_.Properties[0].Value } else { $null } }}, "
    "Message); "
    "ConvertTo-Json -InputObject $events -Depth 3 -Compress"
)

GROUP_MINUTES = 10  # events this close together belong to the same blackout


def _hex(code):
    return f'0x{int(code):08X}'


def events_from_json(text):
    """Turns PowerShell's JSON into a list of {'time', 'id', 'bugcheck'} (newest first)."""
    if not text or not text.strip():
        return []
    data = json.loads(text)
    if isinstance(data, dict):
        data = [data]
    events = []
    for item in data:
        if not item:
            continue
        provider = item.get('ProviderName') or ''
        event_id = int(item['Id'])
        if event_id == 1001 and 'SystemErrorReporting' not in provider:
            continue            # event 1001 also exists for other, unrelated programs
        bugcheck = None
        if event_id == 41 and item.get('Bugcheck'):
            bugcheck = _hex(item['Bugcheck'])             # 0 (no crash) is skipped above
        elif event_id == 1001:
            found = re.search(r'0x[0-9a-fA-F]{1,8}', item.get('Message') or '')
            if found and int(found.group(), 16) != 0:
                bugcheck = _hex(int(found.group(), 16))
        events.append({
            'time': datetime.fromisoformat(item['Time']),
            'id': event_id,
            'bugcheck': bugcheck,
        })
    events.sort(key=lambda e: e['time'], reverse=True)
    return events


def group_into_blackouts(events):
    """One blackout usually writes 2-3 events. Joins them. Returns the newest first.

    Each blackout is {'time': earliest event time, 'bugcheck': code or None}."""
    blackouts = []
    for event in sorted(events, key=lambda e: e['time']):
        last = blackouts[-1] if blackouts else None
        if last and event['time'] - last['last_time'] <= timedelta(minutes=GROUP_MINUTES):
            last['last_time'] = event['time']
            last['bugcheck'] = last['bugcheck'] or event['bugcheck']
        else:
            blackouts.append({'time': event['time'], 'last_time': event['time'],
                              'bugcheck': event['bugcheck']})
    return [{'time': b['time'], 'bugcheck': b['bugcheck']} for b in reversed(blackouts)]


def read_shutdown_events(days=7):
    script = EVENT_SCRIPT.replace('DAYS', str(int(days)))
    result = subprocess.run(
        ['powershell', '-NoProfile', '-NonInteractive', '-Command', script],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or 'PowerShell returned an error')
    return events_from_json(result.stdout)