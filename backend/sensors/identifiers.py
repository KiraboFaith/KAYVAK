"""Identifiers for the before/after hardware snapshot (feedback document, section 3.1)."""
import hashlib
import hmac
import json
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from django.conf import settings

# Serials that only mean "the maker did not fill this in". Comparing them tells us nothing.
PLACEHOLDER_SERIALS = {
    'none', 'unknown', 'default string', 'to be filled by o.e.m.', 'not available',
    'n/a', 'serial number', 'system serial number',
}

DISK_SCRIPT = (
    "$out = Get-PhysicalDisk | ForEach-Object { [pscustomobject]@{ "
    "Model = $_.FriendlyName; Serial = $_.SerialNumber; "
    "MediaType = [string]$_.MediaType; Size = [int64]$_.Size } }; "
    "ConvertTo-Json -InputObject @($out) -Compress"
)

RAM_SCRIPT = (
    "$out = Get-CimInstance Win32_PhysicalMemory | ForEach-Object { [pscustomobject]@{ "
    "Slot = $_.DeviceLocator; Manufacturer = $_.Manufacturer; PartNumber = $_.PartNumber; "
    "Serial = $_.SerialNumber; Capacity = [int64]$_.Capacity } }; "
    "ConvertTo-Json -InputObject @($out) -Compress"
)

# The screen's identity (EDID) comes back as arrays of numbers: turn them into letters.
DISPLAY_SCRIPT = (
    "function ToText($codes) { (@($codes) | Where-Object { $_ -ne 0 } "
    "| ForEach-Object { [char]$_ }) -join '' }; "
    "$out = Get-CimInstance -Namespace root\\wmi -ClassName WmiMonitorID | ForEach-Object { "
    "[pscustomobject]@{ Manufacturer = ToText $_.ManufacturerName; "
    "Product = ToText $_.ProductCodeID; Serial = ToText $_.SerialNumberID; "
    "Year = [int]$_.YearOfManufacture } }; "
    "ConvertTo-Json -InputObject @($out) -Compress"
)

OS_SCRIPT = (
    "$os = Get-CimInstance Win32_OperatingSystem; "
    "[pscustomobject]@{ InstallDate = $os.InstallDate.ToString('s'); "
    "Version = $os.Version; Build = $os.BuildNumber } | ConvertTo-Json -Compress"
)


def clean(value):
    """Trimmed text, or None when there is nothing in it."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def hash_serial(value):
    """Privacy: we never store a serial number, only a short fingerprint of it.

    The same serial always gives the same fingerprint on this installation, so we can
    tell whether a part changed without keeping the serial itself. (The fingerprint uses
    Django's SECRET_KEY, so keep that key the same between the two scans.)
    Returns None when the maker left the serial empty or filled in a placeholder.
    """
    text = clean(value)
    if text is None:
        return None
    lowered = text.lower()
    text = lowered.strip('. ')       # some NVMe serials end in a dot
    if not text or lowered in PLACEHOLDER_SERIALS or text in PLACEHOLDER_SERIALS or set(text) <= {'0'}:
        return None
    digest = hmac.new(settings.SECRET_KEY.encode(), text.encode(), hashlib.sha256)
    return digest.hexdigest()[:16]


def _as_list(text):
    data = json.loads(text) if text else []
    if isinstance(data, dict):   # PowerShell gives one object, not a list, for a single item
        data = [data]
    return data or []


def disks_from_json(text):
    disks = []
    for d in _as_list(text):
        size = d.get('Size')
        disks.append({
            'model': clean(d.get('Model')) or 'Unknown drive',
            'media_type': clean(d.get('MediaType')) or '',
            'size_gb': round(size / 1e9) if size else None,   # drive makers count in 1000s
            'serial_hash': hash_serial(d.get('Serial')),
        })
    return disks


def ram_from_json(text):
    sticks = []
    for d in _as_list(text):
        capacity = d.get('Capacity')
        sticks.append({
            'slot': clean(d.get('Slot')) or '',
            'manufacturer': clean(d.get('Manufacturer')) or '',
            'part_number': clean(d.get('PartNumber')) or '',
            'capacity_gb': round(capacity / 1024 ** 3) if capacity else None,
            'serial_hash': hash_serial(d.get('Serial')),
        })
    return sticks


def displays_from_json(text):
    screens = []
    for d in _as_list(text):
        year = d.get('Year')
        screens.append({
            'manufacturer': clean(d.get('Manufacturer')) or '',
            'product_code': clean(d.get('Product')) or '',
            'year': year if year else None,
            'serial_hash': hash_serial(d.get('Serial')),
        })
    return screens


def windows_from_json(text):
    data = json.loads(text)
    return {
        'install_date': clean(data.get('InstallDate')),
        'version': clean(data.get('Version')),
        'build': clean(data.get('Build')),
    }


def _local_name(tag):
    return tag.split('}')[-1]   # removes the XML namespace


def _whole_number(text):
    text = (text or '').strip()
    return int(text) if text.isdigit() else None


def battery_identity_from_xml(path):
    """Who made this battery, when, and how many cycles it has done (powercfg XML report)."""
    root = ET.parse(path).getroot()
    for item in root.iter():
        if _local_name(item.tag) != 'Battery':
            continue
        fields = {_local_name(child.tag): (child.text or '') for child in item}
        if 'DesignCapacity' not in fields and 'SerialNumber' not in fields:
            continue
        return {
            'name': clean(fields.get('Id')) or '',
            'manufacturer': clean(fields.get('Manufacturer')) or '',
            'manufacture_date': clean(fields.get('ManufactureDate')) or '',
            'design_capacity': _whole_number(fields.get('DesignCapacity')),
            'cycle_count': _whole_number(fields.get('CycleCount')),
            'serial_hash': hash_serial(fields.get('SerialNumber')),
        }
    return None


# The five parts of a snapshot, in the order we show them.
SECTIONS = ('disks', 'ram', 'battery', 'display', 'windows')


def collect_snapshot(run, read_battery_report):
    """Builds one snapshot.

    run(script) runs a PowerShell script and returns its text.
    read_battery_report() writes the battery XML report and returns its file path.
    A part that cannot be read is saved as None (not checked), with the reason in "errors",
    so one failure never stops the rest and we never pretend something was checked.
    """
    data = {'version': 1, 'taken_at': datetime.now(timezone.utc).isoformat(), 'errors': {}}

    def read(name, getter):
        try:
            data[name] = getter()
        except Exception as error:
            data[name] = None
            data['errors'][name] = str(error)[:200]

    # The five reads do not depend on each other and mostly wait on Windows, so they run
    # at the same time. The scan then takes about as long as the slowest one, not the sum.
    jobs = {
        'disks': lambda: disks_from_json(run(DISK_SCRIPT)),
        'ram': lambda: ram_from_json(run(RAM_SCRIPT)),
        'battery': lambda: battery_identity_from_xml(read_battery_report()),
        'display': lambda: displays_from_json(run(DISPLAY_SCRIPT)),
        'windows': lambda: windows_from_json(run(OS_SCRIPT)),
    }
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        for name, getter in jobs.items():
            pool.submit(read, name, getter)   # leaving the "with" waits for all five
    return data


def collect_snapshot_from_windows():
    """The real thing: asks this Windows laptop. Only fixed commands are ever run."""
    from sensors.management.commands import collect_windows as cw

    def read_battery_report():
        cw.read_battery()          # makes powercfg write the XML report
        return cw.BATTERY_REPORT_PATH

    return collect_snapshot(cw.run_powershell, read_battery_report)


def snapshot_summary(snapshot):
    """Small description of a saved snapshot for lists (no serial fingerprints)."""
    data = snapshot.data
    return {
        'id': snapshot.id,
        'label': snapshot.label,
        'created': snapshot.created.isoformat(),
        'checked': [s for s in SECTIONS if data.get(s) is not None],
        'unchecked': [s for s in SECTIONS if data.get(s) is None],
        'errors': data.get('errors', {}),
    }