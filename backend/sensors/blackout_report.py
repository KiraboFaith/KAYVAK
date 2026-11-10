"""Turns a blackout plus the last saved readings into plain words.

Honest rule: if the evidence does not show the cause, we say "unknown". A confident wrong
cause is worse than no cause."""
from datetime import timedelta

LOW_CHARGE = 5                      # at or below this, not charging: the battery most likely ran flat
READING_MAX_AGE = timedelta(minutes=30)   # older readings are too old to explain a blackout

CAUSE_CRASH = 'crash'
CAUSE_BATTERY = 'battery'
CAUSE_UNKNOWN = 'unknown'


def last_known_state(event_time):
    """The newest saved reading from BEFORE the blackout, with its hottest drive temperature."""
    from .models import HealthReading
    reading = HealthReading.objects.filter(timestamp__lte=event_time).first()  # newest first
    if reading is None:
        return None
    temps = [d.temperature for d in reading.disks.all() if d.temperature is not None]
    return {
        'time': reading.timestamp,
        'charge_percent': reading.charge_percent,
        'charging': reading.charging,
        'drive_temp': max(temps) if temps else None,
    }


def _age_text(delta):
    minutes = int(delta.total_seconds() // 60)
    if minutes < 1:
        return 'less than a minute'
    if minutes < 60:
        return f'{minutes} minutes'
    if minutes < 60 * 48:
        return f'{minutes // 60} hours'
    return f'{minutes // (60 * 24)} days'


def build_report(event_time, bugcheck, last):
    """Returns (cause, subject, body). `last` is the dict from last_known_state, or None."""
    restarted = event_time.strftime('%d %b %Y, %H:%M')
    lines = []
    cause = CAUSE_UNKNOWN
    age = (event_time - last['time']) if last else None

    if bugcheck:
        cause = CAUSE_CRASH
        lines.append(f'Windows crashed (blue screen) with stop code {bugcheck}.')
        lines.append('Search that code online to find what it means.')
    elif (last and last['charge_percent'] is not None and last['charging'] is False
          and last['charge_percent'] <= LOW_CHARGE and age <= READING_MAX_AGE):
        cause = CAUSE_BATTERY
        lines.append(f"The battery was at {last['charge_percent']:.0f}% and not charging "
                     'at the last check, so it most likely ran flat.')

    if cause == CAUSE_UNKNOWN:
        lines.append('The cause is unknown. Windows only recorded that the laptop '
                     'did not shut down properly.')
        lines.append('Possible reasons: overheating, a faulty charger or battery, '
                     'or a hardware fault. KAYVAK cannot tell which.')

    lines.append('')
    if last:
        lines.append(f"Last time KAYVAK saw the laptop running: {last['time']:%d %b %Y, %H:%M} "
                     f"({_age_text(age)} before the restart).")
        charge = last['charge_percent']
        lines.append('- Battery charge: ' + ('not reported' if charge is None else f'{charge:.0f}%'))
        state = last['charging']
        lines.append('- Charging: ' + ('not reported' if state is None else ('yes' if state else 'no')))
        temp = last['drive_temp']
        lines.append('- Drive temperature: ' + ('not reported' if temp is None else f'{temp:.0f} °C'))
        if age > READING_MAX_AGE:
            lines.append('That reading is old, so it cannot explain this blackout.')
    else:
        lines.append('KAYVAK had no saved readings from before this blackout.')

    short = {CAUSE_CRASH: 'crashed', CAUSE_BATTERY: 'probably ran out of battery',
             CAUSE_UNKNOWN: 'shut down unexpectedly'}[cause]
    subject = f'KAYVAK: your laptop {short}'
    body = (f'Windows recorded an unexpected shutdown when the laptop restarted on {restarted}.\n\n'
            + '\n'.join(lines)
            + '\n\nKAYVAK tells you what Windows and KAYVAK recorded. It does not guarantee the cause.')
    return cause, subject, body