import json
import os
import platform
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand, CommandError

from sensors.analysis import analyse
from sensors.models import DiskReading, HealthReading, NotificationSetting
from sensors.notify import (
    TOAST_TITLE, decide_alert, decide_low_charge_warning, show_windows_toast,
    toast_body, urgent_email_text, urgent_findings,
)
from sensors.outbox import send_or_queue
CHECK_TIME_LIMIT = 60  # NFR-03: a standard check should finish within 60 seconds
# Drive: a health WORD from Windows is not a measurement. "Healthy" alone tells us nothing
# about how much life is left, so it gives no number. "Warning" and "Unhealthy" are real
# signals, so they are mapped to these two numbers (our own simple mapping).
BAD_STATUS_TO_HEALTH = {'Warning': 60.0, 'Unhealthy': 20.0}

DRIVE_SCRIPT = (
    "$disks = Get-PhysicalDisk | ForEach-Object { "
    "$wear = $null; "
    "try { $wear = ($_ | Get-StorageReliabilityCounter -ErrorAction Stop).Wear } catch {} ; "
    "[pscustomobject]@{ Name = $_.FriendlyName; MediaType = [string]$_.MediaType; "
    "Health = [string]$_.HealthStatus; Wear = $wear } }; "
    "ConvertTo-Json -InputObject @($disks) -Compress"
)

# Early-warning numbers for every disk. Needs an administrator terminal, otherwise the
# numbers come back empty (null) and we save the disk with empty numbers.
DISK_DETAIL_SCRIPT = (
    "$out = foreach ($d in Get-PhysicalDisk) { "
    "$rc = $null; "
    "try { $rc = $d | Get-StorageReliabilityCounter -ErrorAction Stop } catch {} ; "
    "[pscustomobject]@{ "
    "DeviceId = [int]$d.DeviceId; Name = $d.FriendlyName; "
    "MediaType = [string]$d.MediaType; Health = [string]$d.HealthStatus; "
    "Temperature = $rc.Temperature; PowerOnHours = $rc.PowerOnHours; "
    "LoadUnload = $rc.LoadUnloadCycleCount; ReadErrors = $rc.ReadErrorsTotal; "
    "ReadUncorrected = $rc.ReadErrorsUncorrected; Wear = $rc.Wear } }; "
    "ConvertTo-Json -InputObject @($out) -Compress"
)

CHARGE_SCRIPT = (
    "Get-CimInstance Win32_Battery | Select-Object -First 1 "
    "EstimatedChargeRemaining, BatteryStatus | ConvertTo-Json -Compress"
)

# Win32_Battery BatteryStatus codes (from Microsoft's documentation).
# 1 = discharging, 4 = low, 5 = critical: running on the battery.
# 2 = on AC power, 3 = fully charged, 6-9 and 11 = charging or partly charged: plugged in.
ON_BATTERY_CODES = {1, 4, 5}
PLUGGED_IN_CODES = {2, 3, 6, 7, 8, 9, 11}

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

def battery_cycles_from_xml(path):
    """Charge-cycle count from powercfg's battery report. None if the report has none."""
    root = ET.parse(path).getroot()
    for item in root.iter():
        if local_name(item.tag) == 'CycleCount' and item.text and item.text.strip().isdigit():
            return int(item.text.strip())
    return None


BATTERY_REPORT_PATH = os.path.join(tempfile.gettempdir(), 'kayvak_battery.xml')


def read_battery_cycles():
    """Reads the report that read_battery() just wrote, so call it right after."""
    return battery_cycles_from_xml(BATTERY_REPORT_PATH)

def read_battery():
    path = BATTERY_REPORT_PATH
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
    """Worst measured drive wins. Returns None when Windows gave nothing we can trust.

    - Wear is used only for non-HDD disks. Spinning hard drives report Wear 0 even though
      they cannot measure it, so 0 there means "not reported", not "perfect".
    - "Warning" / "Unhealthy" from Windows are real signals and are used on any disk.
    - "Healthy" alone gives no number (None = not measured).
    """
    disks = json.loads(text)
    if isinstance(disks, dict):
        disks = [disks]
    if not disks:
        raise RuntimeError('Windows listed no drives')
    values = []
    for disk in disks:
        if disk.get('Wear') is not None and disk.get('MediaType') != 'HDD':
            values.append(100.0 - float(disk['Wear']))
        if disk.get('Health') in BAD_STATUS_TO_HEALTH:
            values.append(BAD_STATUS_TO_HEALTH[disk['Health']])
    if not values:
        return None
    return round(max(0.0, min(100.0, min(values))), 1)

def read_drive():
    return drive_percent_from_json(run_powershell(DRIVE_SCRIPT))

def disk_details_from_json(text):
    """Turns PowerShell's JSON into one dictionary per disk (missing numbers stay None)."""
    disks = json.loads(text)
    if isinstance(disks, dict):
        disks = [disks]
    return [
        {
            'device_id': int(disk['DeviceId']),
            'name': disk.get('Name') or 'Unknown disk',
            'media_type': disk.get('MediaType') or '',
            'health_status': disk.get('Health') or '',
            'temperature': disk.get('Temperature'),
            'power_on_hours': disk.get('PowerOnHours'),
            'load_unload_cycles': disk.get('LoadUnload'),
            'read_errors_total': disk.get('ReadErrors'),
            'read_errors_uncorrected': disk.get('ReadUncorrected'),
            'wear': disk.get('Wear'),
        }
        for disk in disks
    ]


def read_disk_details():
    return disk_details_from_json(run_powershell(DISK_DETAIL_SCRIPT))

def charge_from_json(text):
    """Returns (charge_percent, charging). Anything Windows does not tell us stays None."""
    if not text:
        return None, None
    data = json.loads(text)
    percent = data.get('EstimatedChargeRemaining')
    status = data.get('BatteryStatus')
    charging = None
    if status in ON_BATTERY_CODES:
        charging = False
    elif status in PLUGGED_IN_CODES:
        charging = True
    return (float(percent) if percent is not None else None), charging


def read_charge():
    return charge_from_json(run_powershell(CHARGE_SCRIPT))

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
        self.emailed = set()  # urgent problems already sent by email
        self.low_charge_warned = False
    
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
        charge_percent, charging = None, None   # not every laptop reports these: not an error
        try:
            charge_percent, charging = read_charge()
        except Exception as error:
            self.stdout.write(f'Charge level not read: {error}')
        try:
            battery = read_battery()
        except Exception as error:
            self.stderr.write(f'Battery not read, reading skipped: {error}')
            return
        battery_cycles = None   # some laptops do not report cycles: that is fine, not an error
        try:
            battery_cycles = read_battery_cycles()
        except Exception as error:
            self.stdout.write(f'Battery cycles not read: {error}')
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
            battery_cycles=battery_cycles,
            drive_health=drive,
            licence_valid=licence_valid,
            suspected_malware=suspected_malware,
            source='windows',
            licence_checked=licence_checked,
            malware_checked=malware_checked,
            check_seconds=seconds,
            charge_percent=charge_percent,
            charging=charging,
        )
        self.stdout.write(f'Inserted: {reading} (took {seconds} s)')
        self.save_disk_details(reading)
        self.alert_if_urgent(reading)
        self.email_alerts(reading)
        
    def save_disk_details(self, reading):
        """Saves the per-disk numbers. If this fails, the main reading is already saved."""
        try:
            for disk in read_disk_details():
                DiskReading.objects.create(reading=reading, **disk)
        except Exception as error:
            self.stderr.write(f'Disk details not saved: {error}')    

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
            
    def email_alerts(self, reading):
        """Emails urgent problems and a low-battery warning, if the owner agreed to email."""
        setting = NotificationSetting.current()
        urgent = urgent_findings(analyse(reading))
        email_now, self.emailed = decide_alert(
            setting.email_enabled, {f['component'] for f in urgent}, self.emailed)
        if email_now:
            subject, body = urgent_email_text(urgent)
            self.stdout.write(f'Urgent email: {send_or_queue(subject, body)}')

        warn, self.low_charge_warned = decide_low_charge_warning(
            reading.charge_percent, reading.charging, self.low_charge_warned)
        if warn and setting.email_enabled:
            percent = f'{reading.charge_percent:.0f}'
            result = send_or_queue(
                f'KAYVAK warning: battery at {percent}%',
                f'Your laptop battery is at {percent}% and it is not charging. '
                'Plug it in soon or it may switch off.')
            self.stdout.write(f'Low battery email: {result}')