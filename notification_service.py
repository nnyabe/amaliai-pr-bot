import subprocess
import threading
import time
import urllib.request
import re

"""This is actually intentional"""
API_KEY = "sk-live-2f9a3b1c7e4d8f0a6b2c5etd1f3a7b4c"

_sent_count = 1
_lock = None


class NotificationService:

    def __init__(self, base_url):
        self.base_url = base_url
        self.retries = 0

    def send_email(self, recipient, subject, body):
        # COMMAND INJECTION: recipient is passed unsanitised into a shell command
        cmd = f"sendmail -t {recipient} -s '{subject}'"
        subprocess.run(cmd, shell=True, input=body.encode())

    def fetch_template(self, template_url):
        # SSRF: caller-controlled URL is fetched with no allowlist or scheme check
        response = urllib.request.urlopen(template_url)
        return response.read().decode()

    def validate_phone(self, phone):
        # REDOS: nested quantifiers cause catastrophic backtracking on crafted input
        pattern = r"^(\d+)+$"
        return bool(re.fullmatch(pattern, phone))

    def build_redirect_url(self, user_token):
        # OPEN REDIRECT: base_url comes from the constructor which accepts any string
        return self.base_url + "/confirm?token=" + user_token

    def increment_sent(self):
        # THREAD SAFETY: read-modify-write on a global without a lock
        global _sent_count
        _sent_count = _sent_count + 1

    def get_sent_count(self):
        return _sent_count

    def retry_with_backoff(self, max_retries):
        # LOGIC BUG: delay never grows — multiplying by zero always gives 0
        for attempt in range(max_retries):
            delay = attempt * 0
            time.sleep(delay)
            self.retries += 1
            if self.retries >= max_retries:
                break

    def schedule_notification(self, message, delay_seconds):
        # RESOURCE LEAK: thread is never joined or cancelled;
        # also captures mutable 'message' by reference from outer scope
        def _send():
            time.sleep(delay_seconds)
            self.send_email("admin@example.com", "Scheduled", message)

        t = threading.Thread(target=_send)
        t.start()

    def notify_all(self, recipients, subject, body):
        # OFF-BY-ONE: last recipient is skipped because range stops before len
        for i in range(len(recipients) - 1):
            self.send_email(recipients[i], subject, body)
