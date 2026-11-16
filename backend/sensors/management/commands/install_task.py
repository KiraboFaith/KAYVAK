import platform
import subprocess
import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

BACKEND_DIR = Path(__file__).resolve().parents[3]    # the folder that holds manage.py
MANAGE_PY = BACKEND_DIR / 'manage.py'

COLLECT_TASK = 'KAYVAK collector'
BLACKOUT_TASK = 'KAYVAK blackout check'
TASK_NAMES = (COLLECT_TASK, BLACKOUT_TASK)


def ps_quote(text):
    """Wraps text in PowerShell single quotes. A ' inside is written as '' (PowerShell's rule)."""
    return "'" + str(text).replace("'", "''") + "'"


def register_script(task_name, manage_args, trigger, python=None, manage_py=None, workdir=None):
    """The PowerShell that creates (or replaces) one scheduled task.

    - It runs `python manage.py <manage_args>` from the backend folder.
    - Highest run level: reading the disk counters needs administrator rights.
    - AllowStartIfOnBatteries / DontStopIfGoingOnBatteries: Windows' default is to NOT run
      scheduled tasks on battery, which on a laptop is exactly when the readings matter.
    - StartWhenAvailable: a run missed because the laptop was off happens when it wakes.
    """
    python = python or sys.executable
    manage_py = manage_py or MANAGE_PY
    workdir = workdir or BACKEND_DIR
    argument = '"' + str(manage_py) + '" ' + manage_args   # the script path may contain spaces
    return (
        f"$action = New-ScheduledTaskAction -Execute {ps_quote(python)} "
        f"-Argument {ps_quote(argument)} "
        f"-WorkingDirectory {ps_quote(workdir)}; "
        f"$trigger = {trigger}; "
        "$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME "
        "-LogonType Interactive -RunLevel Highest; "
        "$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries "
        "-DontStopIfGoingOnBatteries -StartWhenAvailable "
        "-ExecutionTimeLimit (New-TimeSpan -Minutes 10); "
        f"Register-ScheduledTask -TaskName {ps_quote(task_name)} -Action $action "
        "-Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null"
    )


def hourly_trigger():
    # A duration is given on purpose: older Windows versions reject a repeat with no end.
    return ("New-ScheduledTaskTrigger -Once -At (Get-Date) "
            "-RepetitionInterval (New-TimeSpan -Hours 1) "
            "-RepetitionDuration (New-TimeSpan -Days 3650)")


def install_scripts(python=None, manage_py=None, workdir=None):
    """(task name, PowerShell) for every task KAYVAK needs."""
    return [
        (COLLECT_TASK,
         register_script(COLLECT_TASK, 'collect_windows --once', hourly_trigger(),
                         python, manage_py, workdir)),
        (BLACKOUT_TASK,
         register_script(BLACKOUT_TASK, 'check_blackout', 'New-ScheduledTaskTrigger -AtLogOn',
                         python, manage_py, workdir)),
    ]


def remove_script(task_name):
    return (f"Unregister-ScheduledTask -TaskName {ps_quote(task_name)} "
            "-Confirm:$false -ErrorAction Stop")


def run_powershell(script):
    result = subprocess.run(
        ['powershell', '-NoProfile', '-NonInteractive', '-Command', script],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or 'PowerShell returned an error')


class Command(BaseCommand):
    help = ('Sets up Windows scheduled tasks so KAYVAK collects a reading every hour and checks '
            'for unexpected shutdowns at every login, without a terminal being open. '
            'Run it from an administrator terminal.')

    def add_arguments(self, parser):
        parser.add_argument('--remove', action='store_true', help='delete the KAYVAK scheduled tasks')
        parser.add_argument('--dry-run', action='store_true',
                            help='only print the PowerShell that would run (works on any computer)')

    def handle(self, *args, **options):
        if options['remove']:
            jobs = [(name, remove_script(name)) for name in TASK_NAMES]
        else:
            jobs = install_scripts()

        if options['dry_run']:
            for name, script in jobs:
                self.stdout.write(f'# {name}\n{script}\n')
            return

        if platform.system() != 'Windows':
            raise CommandError('Scheduled tasks can only be set up on Windows. '
                               'Use --dry-run to see what would run.')
        for name, script in jobs:
            try:
                run_powershell(script)
            except Exception as error:
                raise CommandError(
                    f'Could not {"remove" if options["remove"] else "set up"} "{name}": {error}\n'
                    'Open PowerShell with "Run as administrator" and try again.')
            self.stdout.write(f'{"Removed" if options["remove"] else "Set up"}: {name}')
        if not options['remove']:
            self.stdout.write('Check them in Task Scheduler, or run: Get-ScheduledTask -TaskName "KAYVAK*"')