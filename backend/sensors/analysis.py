BATTERY_WARNING = 60
BATTERY_CRITICAL = 40
DRIVE_WARNING = 70
DRIVE_CRITICAL = 40
# Trend settings (the Knowledge part of MAPE-K: past readings predict the future)
TREND_MIN_READINGS = 5     # fewer readings than this is not enough to call a trend
TREND_STABLE_BAND = 0.1    # a change smaller than this per check counts as "stable"

def _level(value, warning, critical):
    if value < critical:
        return 'Critical'
    if value < warning:
        return 'Warning'
    return None


def analyse(reading):
    findings = []

    # FR-02: battery health
    level = _level(reading.battery_health, BATTERY_WARNING, BATTERY_CRITICAL)
    if level:
        findings.append({
            'component': 'Battery',
            'status': level,
            'type': 'hardware',                                   # FR-04
            'explanation': 'Your battery now holds much less charge than when it was new.',  # FR-06
            'evidence': f'Battery health is {reading.battery_health:.0f}% of original capacity.',  # FR-07
            'advice': (
                'See a technician soon. If the laptop body looks swollen, stop using it.'
                if level == 'Critical' else
                'You can keep using it. Lower screen brightness and close unused apps to save power.'
            ),                                                    # FR-08
        })

    # FR-03: storage drive health
    level = _level(reading.drive_health, DRIVE_WARNING, DRIVE_CRITICAL)
    if level:
        findings.append({
            'component': 'Storage drive',
            'status': level,
            'type': 'hardware',
            'explanation': 'Your storage drive is wearing out and may fail.',
            'evidence': f'Drive health is {reading.drive_health:.0f}%.',
            'advice': (
                'Back up your files now, then see a technician.'
                if level == 'Critical' else
                'Back up your important files soon.'
            ),
        })

    # FR-05: licence
    if not reading.licence_valid:
        findings.append({
            'component': 'Windows licence',
            'status': 'Warning',
            'type': 'software',
            'explanation': 'Your Windows licence is expired or not valid.',
            'evidence': 'The licence check failed.',
            'advice': 'Get a genuine licence. Do not use cracked tools, they can carry viruses.',
        })

    # FR-04: suspected malware
    if reading.suspected_malware:
        findings.append({
            'component': 'Security',
            'status': 'Critical',
            'type': 'software',
            'explanation': 'The laptop may have a virus or harmful software.',
            'evidence': 'Suspicious activity was detected.',
            'advice': 'Run your antivirus scan. If the problem stays, see a technician.',
        })

    # FR-01: overall status = the worst finding
    statuses = [f['status'] for f in findings]
    if 'Critical' in statuses:
        overall = 'Critical'
    elif 'Warning' in statuses:
        overall = 'Warning'
    else:
        overall = 'Good'

    return {'overall': overall, 'findings': findings}

def trend(values, warning, critical):
    """Looks at past readings (oldest first) and says where a value is heading.

    Returns None when there are too few readings. Otherwise returns the
    direction, the average change per check, and how many more checks until
    the value drops below the Warning and Critical limits (0 = already there,
    None = not heading there).
    """
    n = len(values)
    if n < TREND_MIN_READINGS:
        return None

    # Straight-line fit through the readings (least squares), x = check number.
    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    slope = (
        sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values))
        / sum((i - mean_x) ** 2 for i in range(n))
    )

    if abs(slope) < TREND_STABLE_BAND:
        direction = 'stable'
    elif slope < 0:
        direction = 'falling'
    else:
        direction = 'rising'

    current = values[-1]

    def checks_until(limit):
        if current < limit:
            return 0
        if direction != 'falling':
            return None
        return round((current - limit) / -slope)

    return {
        'direction': direction,
        'change_per_check': round(slope, 2),
        'checks_to_warning': checks_until(warning),
        'checks_to_critical': checks_until(critical),
    }