# Cut-offs. Battery = % of original capacity left, drive = % of drive life left.
# These are our own heuristics, so each one says where it comes from.
# Battery 80: the commonly used "battery is worn" reference point (FYP feedback document,
#   Step 2). TODO: replace this note with the source you actually cite.
# Battery 60: our own cut-off for "replacement worth considering". TODO: check it against
#   the technician survey and write the result here.
# Drive 70 and 40: our own cut-offs. TODO: write down why you chose them.
BATTERY_WARNING = 80
BATTERY_CRITICAL = 60
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


# How big a repair each finding justifies. This is the "is a major repair justified?" check.
# 'Major repair' (for example a new motherboard) is deliberately never given: none of the
# checks here can show that a board-level fault exists.
REPAIR_NONE = 'No repair needed yet'
REPAIR_MINOR = 'Minor repair'
REPAIR_SOFTWARE = 'Software fix only'


def uncorrected_read_errors(reading):
    """Total uncorrected read errors across this reading's disks (0 when none are known)."""
    disks = getattr(reading, 'disks', None)
    if disks is None:
        return 0
    return sum(d.read_errors_uncorrected or 0 for d in disks.all())


def analyse(reading):
    findings = []

    # FR-02: battery health
    cycles = getattr(reading, 'battery_cycles', None)   # None = this laptop does not report it
    level = _level(reading.battery_health, BATTERY_WARNING, BATTERY_CRITICAL)
    if level:
        findings.append({
            'component': 'Battery',
            'status': level,
            'type': 'hardware',                                   # FR-04
            'explanation': 'Your battery now holds much less charge than when it was new.',  # FR-06
            'evidence': (                                         # FR-07
                f'Battery health is {reading.battery_health:.0f}% of original capacity '
                f'({100 - reading.battery_health:.0f}% worn).'
                + (f' It has been through {cycles} charge cycles.' if cycles is not None else '')
            ),
            'advice': (
                'See a technician soon. If the laptop body looks swollen, stop using it.'
                if level == 'Critical' else
                'You can keep using it. Lower screen brightness and close unused apps to save power.'
            ),                                                    # FR-08
            'repair': REPAIR_MINOR if level == 'Critical' else REPAIR_NONE,
            'repair_note': (
                'Replacing the battery is a minor repair. This finding alone does not justify '
                'a major repair such as a new motherboard.'
                if level == 'Critical' else
                'A worn battery is normal wear and tear. No repair is needed yet.'
            ),
        })

    # FR-03: storage drive health (None = Windows could not measure it: no finding, no guess)
    level = (
        _level(reading.drive_health, DRIVE_WARNING, DRIVE_CRITICAL)
        if reading.drive_health is not None else None
    )
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
            'repair': REPAIR_MINOR if level == 'Critical' else REPAIR_NONE,
            'repair_note': (
                'Replacing the drive is a part swap, which counts as a minor repair. This finding '
                'alone does not justify a major repair such as a new motherboard.'
                if level == 'Critical' else
                'Back up your files. A replacement drive is not needed yet.'
            ),
        })

    # FR-03 (early warning): uncorrected read errors mean the drive failed to read data back.
    # Any at all is a real signal, so this alone gives a Warning (if health already flagged
    # the drive, that finding stays and this one is skipped).
    errors = uncorrected_read_errors(reading)
    if errors > 0 and not level:
        findings.append({
            'component': 'Storage drive',
            'status': 'Warning',
            'type': 'hardware',
            'explanation': 'Your storage drive has failed to read some data correctly.',
            'evidence': f'Windows counted {errors} uncorrected read errors on this drive.',
            'advice': 'Back up your important files now and check again later. If the number grows, replace the drive.',
            'repair': REPAIR_MINOR,
            'repair_note': (
                'If the errors keep growing, replacing the drive is justified. '
                'It is a part swap, not a major repair.'
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
            'repair': REPAIR_SOFTWARE,
            'repair_note': 'This is fixed with a genuine licence, not a hardware repair.',
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
            'repair': REPAIR_SOFTWARE,
            'repair_note': 'Cleaning the laptop is a software job. This finding does not justify any hardware repair.',
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