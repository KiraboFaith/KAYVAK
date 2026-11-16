from .disk_trends import disk_error_growth

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
# Trend settings (the Knowledge part of MAPE-K: past readings predict the future).
# Time is measured in DAYS, not in "checks": the collector can run every minute or every hour,
# and a prediction must not change meaning when that setting changes.
# Both numbers are our own choices, not from a source. TODO: justify them in the write-up.
TREND_MIN_POINTS = 5      # need readings from at least this many different days
TREND_STABLE_BAND = 0.02  # a change smaller than this many points per day counts as "stable"

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
    # - Any at all is a real signal: Warning.
    # - Errors still being added over the last days mean the drive is failing now: Critical.
    #   This rule is our own heuristic. TODO: test it against real failing drives before
    #   claiming it in the write-up. We have not checked that Windows' counter matches the
    #   SMART attributes used in the Backblaze data.
    # One finding per component: if the health score already flagged the drive, the growth
    # finding replaces it (it says more); a Warning-level error finding never replaces it.
    errors = uncorrected_read_errors(reading)
    growth = disk_error_growth(reading) if errors > 0 else None
    growing = growth is not None and growth['increase'] > 0
    if errors > 0 and (growing or not level):
        if growing:
            findings = [f for f in findings if f['component'] != 'Storage drive']
            evidence = (
                f'Windows counted {errors} uncorrected read errors in total. '
                f'{growth["increase"]} were added in the last {growth["days"]:g} days '
                f'(about {growth["per_day"]:g} a day) on {growth["name"]}.'
            )
        else:
            evidence = f'Windows counted {errors} uncorrected read errors on this drive.'
            if growth is not None:
                evidence += f' None were added in the last {growth["days"]:g} days.'
        findings.append({
            'component': 'Storage drive',
            'status': 'Critical' if growing else 'Warning',
            'type': 'hardware',
            'explanation': (
                'Your storage drive keeps failing to read data correctly, and it is getting worse.'
                if growing else
                'Your storage drive has failed to read some data correctly.'
            ),
            'evidence': evidence,
            'advice': (
                'Back up your important files today, then see a technician. Do not wait.'
                if growing else
                'Back up your important files now and check again later. If the number grows, replace the drive.'
            ),
            'repair': REPAIR_MINOR,
            'repair_note': (
                'Errors that keep growing justify replacing the drive. '
                'It is a part swap, not a major repair.'
                if growing else
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

def trend(points, warning, critical):
    """Looks at past readings and says where a value is heading, in days.

    points: (day, value) pairs, oldest first. "day" is any number that grows by 1 per day
    (for example date.toordinal()). One point per day is expected (a daily average).

    Returns None when there are too few days of history. Otherwise returns the direction,
    the average change per day, how many days the history covers, and how many more days
    until the value drops below the Warning and Critical limits (0 = already there,
    None = not heading there).
    """
    n = len(points)
    if n < TREND_MIN_POINTS:
        return None

    days = [float(d) for d, _ in points]
    values = [float(v) for _, v in points]
    mean_x = sum(days) / n
    mean_y = sum(values) / n
    spread = sum((x - mean_x) ** 2 for x in days)
    if spread == 0:                      # every point on the same day: no time has passed
        return None

    # Straight-line fit through the readings (least squares), x = day.
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(days, values)) / spread

    if abs(slope) < TREND_STABLE_BAND:
        direction = 'stable'
    elif slope < 0:
        direction = 'falling'
    else:
        direction = 'rising'

    current = values[-1]

    def days_until(limit):
        if current < limit:
            return 0
        if direction != 'falling':
            return None
        return round((current - limit) / -slope)

    return {
        'direction': direction,
        'change_per_day': round(slope, 3),
        'based_on_days': round(days[-1] - days[0]),
        'days_to_warning': days_until(warning),
        'days_to_critical': days_until(critical),
    }