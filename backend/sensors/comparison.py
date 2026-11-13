"""Compares two hardware snapshots: what stayed the same, what changed, what was added or removed.

Rules that keep the result honest:
- A part that could not be read in either scan is "not checked". We never call it unchanged.
- Serial numbers are compared as fingerprints (see identifiers.hash_serial).
- If a serial could be read in only one of the two scans, we fall back to model and size,
  so a missing serial does not cause a false alarm.
"""

# A battery that has just been fitted should not already have hundreds of charge cycles.
# TODO: this is our own cut-off. Replace this note with where the number comes from.
NEW_BATTERY_CYCLE_LIMIT = 100

LIMITS = (
    'This check cannot see keyboard, hinge, charging-port or screen-cable work, '
    'and it cannot tell whether a repair was needed.'
)


def _match(before, after, strong, weak):
    """Pairs up the same part in both scans.

    strong(item) is the serial fingerprint (or None), weak(item) is a tuple such as
    (model, size). Returns (pairs, removed, added). Each pair is (before, after, note).
    """
    left = list(before)
    right = list(after)
    pairs = []

    for b in list(left):                                   # 1. same serial = same part
        if strong(b) is None:
            continue
        a = next((x for x in right if strong(x) == strong(b)), None)
        if a is not None:
            pairs.append((b, a, ''))
            left.remove(b)
            right.remove(a)

    for b in list(left):                                   # 2. no serial in one scan
        a = next(
            (x for x in right
             if weak(x) == weak(b) and (strong(x) is None or strong(b) is None)),
            None,
        )
        if a is not None:
            note = '' if strong(a) is None and strong(b) is None else 'Serial number could not be read in one of the scans.'
            pairs.append((b, a, note))
            left.remove(b)
            right.remove(a)

    return pairs, left, right


def _items(pairs, removed, added, label):
    items = [{'state': 'unchanged', 'label': label(b), 'detail': note} for b, _a, note in pairs]
    items += [{'state': 'removed', 'label': label(b), 'detail': 'Present in the first scan only.'} for b in removed]
    items += [{'state': 'added', 'label': label(a), 'detail': 'Present in the second scan only.'} for a in added]
    return items


def _result(name, items, notes=None):
    changed = [i for i in items if i['state'] != 'unchanged']
    removed = sum(1 for i in items if i['state'] == 'removed')
    added = sum(1 for i in items if i['state'] == 'added')
    if not changed:
        summary = 'No change.'
    else:
        summary = f'{removed} removed, {added} added.'
    return {
        'component': name,
        'status': 'changed' if changed else 'unchanged',
        'summary': summary,
        'items': items,
        'notes': notes or [],
    }


def _not_checked(name, reason):
    return {'component': name, 'status': 'not_checked', 'summary': reason, 'items': [], 'notes': []}


def _both(name, before, after):
    """None if both scans have this part, otherwise the "not checked" result."""
    if before is None or after is None:
        which = 'either scan' if before is None and after is None else (
            'the first scan' if before is None else 'the second scan')
        return _not_checked(name, f'Could not be read in {which}, so we cannot say whether it changed.')
    return None

def disk_label(d):
    size = f'{d["size_gb"]} GB' if d.get('size_gb') else 'size unknown'
    return f'{d["model"]} ({d["media_type"] or "type unknown"}, {size})'


def ram_label(r):
    size = f'{r["capacity_gb"]} GB' if r.get('capacity_gb') else 'size unknown'
    part = r['part_number'] or 'part number unknown'
    return f'{size} {part} (slot {r["slot"] or "?"})'


def display_label(s):
    year = f' ({s["year"]})' if s.get('year') else ''
    return f'{s["manufacturer"]} {s["product_code"]}{year}'.strip() or 'Screen'

def compare_disks(before, after):
    name = 'Storage drive'
    missing = _both(name, before, after)
    if missing:
        return missing

    

    pairs, removed, added = _match(
        before, after,
        strong=lambda d: d.get('serial_hash'),
        weak=lambda d: (d['model'], d.get('size_gb')),
    )
    return _result(name, _items(pairs, removed, added, disk_label))


def compare_ram(before, after):
    name = 'Memory (RAM)'
    missing = _both(name, before, after)
    if missing:
        return missing

    def label(r):
        size = f'{r["capacity_gb"]} GB' if r.get('capacity_gb') else 'size unknown'
        part = r['part_number'] or 'part number unknown'
        return f'{size} {part} (slot {r["slot"] or "?"})'

    pairs, removed, added = _match(
        before, after,
        strong=lambda r: r.get('serial_hash'),
        weak=lambda r: (r['part_number'], r.get('capacity_gb'), r['slot']),
    )
    total_before = sum(r.get('capacity_gb') or 0 for r in before)
    total_after = sum(r.get('capacity_gb') or 0 for r in after)
    notes = []
    if total_after < total_before:
        notes.append(
            f'Total memory went down ({total_before} GB to {total_after} GB). '
            'A good part may have been swapped for a smaller one.'
        )
    elif total_after > total_before:
        notes.append(f'Total memory went up ({total_before} GB to {total_after} GB).')
    return _result(name, _items(pairs, removed, added, ram_label), notes)


def compare_battery(before, after):
    name = 'Battery'
    missing = _both(name, before, after)
    if missing:
        return missing

    cycles_before, cycles_after = before.get('cycle_count'), after.get('cycle_count')
    cycles_dropped = (
        cycles_before is not None and cycles_after is not None and cycles_after < cycles_before
    )

    replaced = None   # None = we cannot tell
    if before.get('serial_hash') and after.get('serial_hash'):
        replaced = before['serial_hash'] != after['serial_hash']
    else:
        for field in ('manufacturer', 'manufacture_date', 'design_capacity'):
            if before.get(field) and after.get(field) and before[field] != after[field]:
                replaced = True
                break
    if cycles_dropped:
        replaced = True

    label = after.get('name') or before.get('name') or 'Battery'
    detail = []
    if cycles_before is not None and cycles_after is not None:
        detail.append(f'Charge cycles: {cycles_before} then {cycles_after}.')
    notes = []

    if replaced is None:
        return _not_checked(
            name, 'This battery does not report a serial number, so we cannot tell whether it was replaced.')
    if replaced:
        if cycles_dropped:
            detail.append('The cycle count went down, which only happens with a different battery.')
        if cycles_after is not None and cycles_after >= NEW_BATTERY_CYCLE_LIMIT:
            notes.append(
                f'The battery in the second scan has already been through {cycles_after} charge '
                'cycles, so it is not a new battery.'
            )
        state = 'changed'
        summary = 'The battery is a different one.'
    else:
        state = 'unchanged'
        summary = 'No change.'
    return {
        'component': name,
        'status': 'changed' if replaced else 'unchanged',
        'summary': summary,
        'items': [{'state': state, 'label': label, 'detail': ' '.join(detail)}],
        'notes': notes,
    }


def compare_display(before, after):
    name = 'Screen'
    missing = _both(name, before, after)
    if missing:
        return missing

    def label(s):
        year = f' ({s["year"]})' if s.get('year') else ''
        return f'{s["manufacturer"]} {s["product_code"]}{year}'.strip() or 'Screen'

    pairs, removed, added = _match(
        before, after,
        strong=lambda s: s.get('serial_hash'),
        weak=lambda s: (s['manufacturer'], s['product_code'], s.get('year')),
    )
    notes = []
    if removed or added:
        notes.append('Disconnect any external screens before both scans, or they will show up as changes.')
    return _result(name, _items(pairs, removed, added, display_label), notes)


def compare_windows(before, after):
    name = 'Windows install'
    missing = _both(name, before, after)
    if missing:
        return missing
    first, second = before.get('install_date'), after.get('install_date')
    if not first or not second:
        return _not_checked(name, 'Windows did not give us the install date, so we cannot tell.')
    notes = []
    if before.get('build') and after.get('build') and before['build'] != after['build']:
        notes.append(f'Windows was updated (build {before["build"]} to {after["build"]}). This is normal.')
    if first != second:
        return {
            'component': name, 'status': 'changed',
            'summary': 'Windows was installed again between the scans.',
            'items': [{'state': 'changed', 'label': 'Windows', 'detail': f'Install date: {first} then {second}.'}],
            'notes': notes,
        }
    return {
        'component': name, 'status': 'unchanged', 'summary': 'No change.',
        'items': [{'state': 'unchanged', 'label': 'Windows', 'detail': f'Installed {first}.'}],
        'notes': notes,
    }


def compare(before, after):
    """before and after are snapshot data dictionaries (see identifiers.collect_snapshot)."""
    components = [
        compare_disks(before.get('disks'), after.get('disks')),
        compare_ram(before.get('ram'), after.get('ram')),
        compare_battery(before.get('battery'), after.get('battery')),
        compare_display(before.get('display'), after.get('display')),
        compare_windows(before.get('windows'), after.get('windows')),
    ]
    return {
        'components': components,
        'changed': [c['component'] for c in components if c['status'] == 'changed'],
        'not_checked': [c['component'] for c in components if c['status'] == 'not_checked'],
        'limits': LIMITS,
    }