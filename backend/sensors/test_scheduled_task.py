"""The scheduled-task script is built as text, so it can be checked on any computer.
Whether Windows accepts it must still be checked on the Windows laptop."""
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from .management.commands import install_task as it


class QuoteTests(SimpleTestCase):
    def test_apostrophe_is_doubled(self):
        self.assertEqual(it.ps_quote("C:\\Faith's files"), "'C:\\Faith''s files'")

    def test_plain_text_is_just_wrapped(self):
        self.assertEqual(it.ps_quote('abc'), "'abc'")


class RegisterScriptTests(SimpleTestCase):
    def script(self, **kw):
        return it.register_script(
            'T', 'collect_windows --once', 'New-ScheduledTaskTrigger -AtLogOn',
            python='C:\\Py\\python.exe', manage_py='C:\\KAYVAK\\backend\\manage.py',
            workdir='C:\\KAYVAK\\backend', **kw)

    def test_runs_the_right_command_from_the_backend_folder(self):
        s = self.script()
        self.assertIn("-Execute 'C:\\Py\\python.exe'", s)
        self.assertIn('"C:\\KAYVAK\\backend\\manage.py" collect_windows --once', s)
        self.assertIn("-WorkingDirectory 'C:\\KAYVAK\\backend'", s)

    def test_laptop_battery_settings_are_set(self):
        s = self.script()
        self.assertIn('-AllowStartIfOnBatteries', s)
        self.assertIn('-DontStopIfGoingOnBatteries', s)
        self.assertIn('-StartWhenAvailable', s)

    def test_runs_elevated_because_disk_counters_need_admin(self):
        self.assertIn('-RunLevel Highest', self.script())

    def test_paths_with_apostrophes_do_not_break_the_quoting(self):
        s = it.register_script('T', 'x', 'trigger', python="C:\\O'Neil\\python.exe",
                               manage_py='m.py', workdir='w')
        self.assertIn("'C:\\O''Neil\\python.exe'", s)


class InstallScriptsTests(SimpleTestCase):
    def test_collector_is_hourly_and_blackout_check_is_at_login(self):
        scripts = dict(it.install_scripts(python='p', manage_py='m', workdir='w'))
        self.assertIn('-Hours 1', scripts[it.COLLECT_TASK])
        self.assertIn('collect_windows --once', scripts[it.COLLECT_TASK])
        self.assertIn('-AtLogOn', scripts[it.BLACKOUT_TASK])
        self.assertIn('check_blackout', scripts[it.BLACKOUT_TASK])

    def test_repeat_has_an_end_for_older_windows(self):
        self.assertIn('-RepetitionDuration', it.hourly_trigger())


class CommandTests(SimpleTestCase):
    def test_dry_run_prints_everything_and_runs_nothing(self):
        out = StringIO()
        with mock.patch.object(it, 'run_powershell') as run:
            call_command('install_task', '--dry-run', stdout=out)
        run.assert_not_called()
        self.assertIn(it.COLLECT_TASK, out.getvalue())
        self.assertIn(it.BLACKOUT_TASK, out.getvalue())

    def test_dry_run_remove_prints_unregister(self):
        out = StringIO()
        call_command('install_task', '--dry-run', '--remove', stdout=out)
        self.assertIn('Unregister-ScheduledTask', out.getvalue())

    def test_refuses_to_run_for_real_off_windows(self):
        with mock.patch.object(it.platform, 'system', return_value='Linux'):
            with self.assertRaises(CommandError):
                call_command('install_task', stdout=StringIO())

    def test_runs_one_script_per_task_on_windows(self):
        with mock.patch.object(it.platform, 'system', return_value='Windows'), \
             mock.patch.object(it, 'run_powershell') as run:
            call_command('install_task', stdout=StringIO())
        self.assertEqual(run.call_count, 2)

    def test_a_failure_tells_the_owner_to_use_administrator(self):
        with mock.patch.object(it.platform, 'system', return_value='Windows'), \
             mock.patch.object(it, 'run_powershell', side_effect=RuntimeError('Access is denied')):
            with self.assertRaises(CommandError) as caught:
                call_command('install_task', stdout=StringIO())
        self.assertIn('administrator', str(caught.exception))