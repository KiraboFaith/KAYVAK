"""How fast a disk's uncorrected read errors are growing.

Windows gives a running total ("3 errors so far"). A total of 3 that has stayed at 3 for a
month is an old scar; a total that went 3, 9, 20 over two days is a disk that is failing now.
So the number that matters is the growth per day, which needs past readings.
"""
from datetime import timedelta

ERROR_WINDOW_DAYS = 7        # how far back to look. Our own choice. TODO: justify in the write-up.
ERROR_MIN_SPAN_DAYS = 1.0    # samples closer together than this say nothing about a daily rate


def error_growth(samples):
    """samples: (datetime, running total) pairs, oldest first.

    Returns None when the samples cannot show growth (fewer than 2, or less than
    ERROR_MIN_SPAN_DAYS between the first and last). Otherwise a dictionary:
    increase (errors added), days (time covered), per_day (increase / days).

    A running total that goes DOWN means the counter was reset (disk swapped, driver
    reset), so only the samples after the last drop are used.
    """
    kept = []
    for when, total in samples:
        if total is None:
            continue
        if kept and total < kept[-1][1]:
            kept = []
        kept.append((when, total))
    if len(kept) < 2:
        return None
    days = (kept[-1][0] - kept[0][0]).total_seconds() / 86400
    if days < ERROR_MIN_SPAN_DAYS:
        return None
    increase = kept[-1][1] - kept[0][1]
    return {'increase': increase, 'days': round(days, 1), 'per_day': round(increase / days, 2)}


def disk_error_growth(reading):
    """The fastest error growth among this reading's disks over the last ERROR_WINDOW_DAYS.

    Returns None when the reading has no saved disks or no disk has enough history.
    The dictionary is the one from error_growth plus the disk's name.
    """
    from .models import DiskReading     # imported here: models import nothing from this file

    disks = getattr(reading, 'disks', None)
    if disks is None:
        return None
    best = None
    for disk in disks.all():
        if disk.read_errors_uncorrected is None:
            continue
        history = (
            DiskReading.objects
            .filter(device_id=disk.device_id, name=disk.name,
                    timestamp__gte=disk.timestamp - timedelta(days=ERROR_WINDOW_DAYS),
                    timestamp__lte=disk.timestamp)
            .exclude(read_errors_uncorrected=None)
            .order_by('timestamp')
        )
        growth = error_growth([(d.timestamp, d.read_errors_uncorrected) for d in history])
        if growth and (best is None or growth['increase'] > best['increase']):
            best = {**growth, 'name': disk.name}
    return best