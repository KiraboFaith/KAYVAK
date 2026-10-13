BATTERY_WARNING = 60
BATTERY_CRITICAL = 40
DRIVE_WARNING = 70
DRIVE_CRITICAL = 40


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