import json
import os
import platform
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand, CommandError

from sensors.analysis import analyse
from sensors.models import HealthReading, NotificationSetting
from sensors.notify import TOAST_TITLE, decide_alert, show_windows_toast, toast_body, urgent_findings
CHECK_TIME_LIMIT = 60  # NFR-03: a standard check should finish within 60 seconds
# Drive: if Windows gives no wear percentage, we turn its health word into a number.
# These three numbers are our own simple mapping, not a measurement.
STATUS_TO_HEALTH = {'Healthy': 100.0, 'Warning': 60.0, 'Unhealthy': 20.0}

DRIVE_SCRIPT = (
    "$disks = Get-PhysicalDisk | ForEach-Object { "
    "$wear = $null; "
    "try { $wear = ($_ | Get-StorageReliabilityCounter -ErrorAction Stop).Wear } catch {} ; "
    "[pscustomobject]@{ Name = $_.FriendlyName; Health = [string]$_.HealthStatus; Wear = $wear } }; "
    "ConvertTo-Json -InputObject @($disks) -Compress"
)

LICENCE_SCRIPT = (
    "Get-CimInstance SoftwareLicensingProduct -Filter 'PartialProductKey IS NOT NULL' "
    "| Where-Object { $_.ApplicationId -eq '55c92734-d682-4d71-983e-d6ec3f16059f' } "
    "| Select-Object -First 1 -ExpandProperty LicenseStatus"
)

MALWARE_SCRIPT = (
    "Get-MpThreat -ErrorAction Stop | Where-Object { $_.IsActive } "
    "| Measure-Object | Select-Object -ExpandProperty Count"
)


def run_powershell(script):
    result = subprocess.run(
        ['powershell', '-NoProfile', '-NonInteractive', '-Command', script],
        capture_output=True, text=True, timeout=90,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or 'PowerShell returned an error')
    return result.stdout.strip()


def local_name(tag):
    return tag.split('}')[-1]  # removes the XML namespace


def battery_percent_from_xml(path):
    """Full-charge capacity divided by design capacity, from powercfg's battery report."""
    root = ET.parse(path).getroot()
    design = full = 0
    for batteries in root.iter():
        if local_name(batteries.tag) != 'Batteries':
            continue
        for battery in batteries:
            for item in battery:
                name = local_name(item.tag)
                if name == 'DesignCapacity':
                    design += int(item.text)
                elif name == 'FullChargeCapacity':
                    full += int(item.text)
        break
    if design <= 0:
        raise RuntimeError('No battery capacity found in the report')
    return round(max(0.0, min(100.0, full / design * 100)), 1)


def read_battery():
    path = os.path.join(tempfile.gettempdir(), 'kayvak_battery.xml')
    result = subprocess.run(
        ['powercfg', '/batteryreport', '/xml', '/output', path],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0 or not os.path.exists(path):
        raise RuntimeError(
            (result.stdout + result.stderr).strip() or 'powercfg could not make a battery report'
        )
    return battery_percent_from_xml(path)


def drive_percent_from_json(text):
    """Worst drive wins. Uses wear when Windows gives it, otherwise the health word."""
    disks = json.loads(text)
    if isinstance(disks, dict):
        disks = [disks]
    values = []
    for disk in disks:
        candidates = []
        if disk.get('Wear') is not None:
            candidates.append(100.0 - float(disk['Wear']))
        if disk.get('Health') in STATUS_TO_HEALTH:
            candidates.append(STATUS_TO_HEALTH[disk['Health']])
        if candidates:
            values.append(min(candidates))
    if not values:
        raise RuntimeError('Windows gave no drive health')
    return round(max(0.0, min(100.0, min(values))), 1)


def read_drive():
    return drive_percent_from_json(run_powershell(DRIVE_SCRIPT))


def read_licence():
    out = run_powershell(LICENCE_SCRIPT)
    if out == '':
        raise RuntimeError('No Windows licence information found')
    return int(out) == 1  # 1 means "Licensed"


def read_malware():
    return int(run_powershell(MALWARE_SCRIPT) or 0) > 0


class Command(BaseCommand):
    help = 'Reads real health values from this Windows laptop and saves them'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alerted = set()  # urgent problems the owner has already been told about
    
    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='take one reading and stop')
        parser.add_argument('--interval', type=int, default=60, help='seconds between readings')

    def handle(self, *args, **options):
        if platform.system() != 'Windows':
            raise CommandError('This collector only works on Windows. Use simulate_health elsewhere.')
        while True:
            self.collect_once()
            if options['once']:
                break
            time.sleep(options['interval'])

    def collect_once(self):
        started = time.monotonic()
        try:
            battery = read_battery()
        except Exception as error:
            self.stderr.write(f'Battery not read, reading skipped: {error}')
            return
        try:
            drive = read_drive()
        except Exception as error:
            self.stderr.write(f'Drive not read, reading skipped: {error}')
            return

        # Licence and security: if Windows will not tell us, we say so instead of guessing.
        licence_valid, licence_checked = True, True
        try:
            licence_valid = read_licence()
        except Exception as error:
            licence_checked = False
            self.stdout.write(f'Licence could not be read, marked as not checked: {error}')
        suspected_malware, malware_checked = False, True
        try:
            suspected_malware = read_malware()
        except Exception as error:
            malware_checked = False
            self.stdout.write(f'Windows Defender could not be read, marked as not checked: {error}')

        seconds = round(time.monotonic() - started, 1)
        if seconds > CHECK_TIME_LIMIT:
            self.stdout.write(f'Warning: the check took {seconds} s (target is {CHECK_TIME_LIMIT} s)')

        reading = HealthReading.objects.create(
            battery_health=battery,
            drive_health=drive,
            licence_valid=licence_valid,
            suspected_malware=suspected_malware,
            source='windows',
            licence_checked=licence_checked,
            malware_checked=malware_checked,
            check_seconds=seconds,
        )
        self.stdout.write(f'Inserted: {reading} (took {seconds} s)')
        self.alert_if_urgent(reading)

    def alert_if_urgent(self, reading):
        """Shows a Windows pop-up for a new urgent problem, if the owner turned notifications on."""
        urgent = urgent_findings(analyse(reading))
        enabled = NotificationSetting.current().enabled
        alert_now, self.alerted = decide_alert(enabled, {f['component'] for f in urgent}, self.alerted)
        if not alert_now:
            return
        try:
            show_windows_toast(TOAST_TITLE, toast_body(urgent))
            self.stdout.write('Urgent alert shown.')
        except Exception as error:
            self.stderr.write(f'Could not show the alert: {error}')