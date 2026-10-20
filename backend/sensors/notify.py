"""Urgent alerts: decides when to alert and shows a Windows pop-up. Nothing leaves the laptop."""
import os
import subprocess

TOAST_TITLE = 'KAYVAK: your laptop needs attention'

# Windows pop-up written in PowerShell, so no extra Python package is needed.
# The text is passed in through environment variables, never pasted into the script.
TOAST_SCRIPT = (
    "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; "
    "$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
    "$text = $xml.GetElementsByTagName('text'); "
    "$text.Item(0).AppendChild($xml.CreateTextNode($env:KAYVAK_TITLE)) | Out-Null; "
    "$text.Item(1).AppendChild($xml.CreateTextNode($env:KAYVAK_BODY)) | Out-Null; "
    "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml); "
    "$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe'; "
    "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show($toast)"
)


def urgent_findings(report):
    """Only Critical problems are urgent. Warnings wait for the owner to open the app."""
    return [f for f in report['findings'] if f['status'] == 'Critical']


def decide_alert(enabled, urgent_now, already_alerted):
    """Returns (alert_now, new_already_alerted).

    - Notifications off: no alert, and we forget what we alerted, so switching them
      on later while a problem is still there gives one alert straight away.
    - Same problem still there: no repeat (otherwise the owner gets a pop-up every minute).
    - A problem goes away and comes back: alert again.
    """
    if not enabled:
        return False, set()
    urgent_now = set(urgent_now)
    return bool(urgent_now - already_alerted), urgent_now


def toast_body(findings):
    first = findings[0]
    body = f"{first['component']}: {first['explanation']} {first['advice']}"
    if len(findings) > 1:
        body += f" ({len(findings) - 1} more urgent problem{'s' if len(findings) > 2 else ''}. Open KAYVAK.)"
    return body


def show_windows_toast(title, body):
    env = dict(os.environ, KAYVAK_TITLE=title, KAYVAK_BODY=body)
    subprocess.run(
        ['powershell', '-NoProfile', '-NonInteractive', '-Command', TOAST_SCRIPT],
        env=env, capture_output=True, text=True, timeout=30, check=True,
    )