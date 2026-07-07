#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
import re
import smtplib
import html as html_module
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_TIMEOUT = 10  # seconds

SMTP_SENDER    = os.environ.get("SMTP_SENDER", "")
SMTP_RECIPIENT = os.environ.get("SMTP_RECIPIENT", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

MAX_BODY_BYTES = 16_384  # 16 KB

PROFILE_LABELS = {
    "individual":   "Individual investor",
    "family-office":"Family office",
    "institution":  "Institutional investor",
    "advisor":      "Advisor or intermediary",
    "corporate":    "Corporate or strategic partner",
    "other":        "Other professional enquiry",
}

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{1,63}$")

FIELD_LIMITS = {
    "firstName": 80,
    "lastName":  80,
    "email":    254,
    "phone":     40,
    "country":  100,
    "profile":   30,
    "message":  2000,
}


def esc(value: str) -> str:
    """HTML-escape a user-supplied string for safe embedding in email body."""
    return html_module.escape(str(value), quote=True)


def validate(data: dict) -> str | None:
    """Return an error message string, or None if data is valid."""
    for field, limit in FIELD_LIMITS.items():
        val = data.get(field, "")
        if not isinstance(val, str):
            return f"Invalid type for field: {field}"
        if len(val) > limit:
            return f"Field '{field}' exceeds maximum length of {limit} characters."

    required = ["firstName", "lastName", "email", "phone", "country", "profile"]
    missing = [f for f in required if not data.get(f, "").strip()]
    if missing:
        return f"Missing required fields: {', '.join(missing)}"

    if not EMAIL_RE.match(data.get("email", "")):
        return "Please provide a valid email address."

    if data.get("profile", "") not in PROFILE_LABELS:
        return "Invalid enquiry profile selection."

    # Both compliance checkboxes must be acknowledged
    for checkbox in ("acknowledgement", "privacy"):
        val = str(data.get(checkbox, "")).lower()
        if val not in ("on", "true", "1", "yes"):
            return "Both compliance acknowledgements are required."

    return None


def send_enquiry_email(data: dict) -> None:
    first   = esc(data.get("firstName", "").strip())
    last    = esc(data.get("lastName", "").strip())
    email   = esc(data.get("email", "").strip())
    phone   = esc(data.get("phone", "").strip())
    country = esc(data.get("country", "").strip())
    profile = esc(PROFILE_LABELS.get(data.get("profile", ""), ""))
    message = esc(data.get("message", "").strip())

    subject = f"New Private Enquiry — {first} {last}"

    # Plain-text version
    body_text = f"""\
Strategic Flow Co. — New Private Enquiry

Name:     {first} {last}
Email:    {email}
Phone:    {phone}
Country:  {country}
Profile:  {profile}
{f'Message:{chr(10)}{message}{chr(10)}' if message else ''}
Both compliance acknowledgements were confirmed by the submitter.
This enquiry was submitted via the Strategic Flow Co. website contact form.
"""

    # HTML version
    message_block = (
        f'<h3 style="margin-top:24px;color:#0a2540">Message</h3>'
        f'<p style="white-space:pre-line;background:#f9f9f9;padding:16px;border-left:3px solid #cba145">{message}</p>'
        if message else ""
    )
    body_html = f"""
<html><body style="font-family:Arial,sans-serif;color:#1a1a2e;max-width:600px">
  <h2 style="color:#0a2540;border-bottom:2px solid #cba145;padding-bottom:8px">
    Strategic Flow Co. — New Private Enquiry
  </h2>
  <table style="width:100%;border-collapse:collapse">
    <tr><td style="padding:8px 0;font-weight:bold;width:160px">Name</td>
        <td style="padding:8px 0">{first} {last}</td></tr>
    <tr style="background:#f9f9f9"><td style="padding:8px 0;font-weight:bold">Email</td>
        <td style="padding:8px 0"><a href="mailto:{email}">{email}</a></td></tr>
    <tr><td style="padding:8px 0;font-weight:bold">Phone</td>
        <td style="padding:8px 0">{phone}</td></tr>
    <tr style="background:#f9f9f9"><td style="padding:8px 0;font-weight:bold">Country</td>
        <td style="padding:8px 0">{country}</td></tr>
    <tr><td style="padding:8px 0;font-weight:bold">Profile</td>
        <td style="padding:8px 0">{profile}</td></tr>
  </table>
  {message_block}
  <p style="color:#888;font-size:12px;margin-top:32px">
    Both compliance acknowledgements were confirmed by the submitter.<br>
    Submitted via the Strategic Flow Co. website contact form.
  </p>
</body></html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"]  = subject
    msg["From"]     = f"Strategic Flow Co. <{SMTP_SENDER}>"
    msg["To"]       = SMTP_RECIPIENT
    msg["Reply-To"] = data.get("email", "").strip()

    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
        server.starttls()
        server.login(SMTP_SENDER, GMAIL_APP_PASSWORD)
        server.sendmail(SMTP_SENDER, SMTP_RECIPIENT, msg.as_string())


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_POST(self):
        if self.path != "/api/contact":
            self.send_response(404)
            self.end_headers()
            return

        # Guard against oversized payloads
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_BODY_BYTES:
            self._json(413, {"ok": False, "error": "Request too large."})
            return

        raw = self.rfile.read(length)

        try:
            data = json.loads(raw)
        except Exception:
            self._json(400, {"ok": False, "error": "Invalid request format."})
            return

        if not isinstance(data, dict):
            self._json(400, {"ok": False, "error": "Invalid request format."})
            return

        error = validate(data)
        if error:
            self._json(400, {"ok": False, "error": error})
            return

        if not GMAIL_APP_PASSWORD or not SMTP_SENDER or not SMTP_RECIPIENT:
            print("ERROR: Email environment variables are not fully configured.")
            self._json(500, {"ok": False, "error": "Email service is not configured."})
            return

        try:
            send_enquiry_email(data)
            self._json(200, {"ok": True})
        except smtplib.SMTPAuthenticationError:
            print("SMTP auth error — check GMAIL_APP_PASSWORD and SMTP_SENDER")
            self._json(500, {"ok": False, "error": "Email authentication failed. Please contact us directly."})
        except smtplib.SMTPException as e:
            print(f"SMTP error: {e}")
            self._json(500, {"ok": False, "error": "Failed to send enquiry. Please try again."})
        except Exception as e:
            print(f"Unexpected error: {e}")
            self._json(500, {"ok": False, "error": "An unexpected error occurred. Please try again."})

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(fmt % args)


if not SMTP_SENDER or not SMTP_RECIPIENT:
    print("WARNING: SMTP_SENDER or SMTP_RECIPIENT is not set. Contact form will not send emails.")

with socketserver.TCPServer(("0.0.0.0", 5000), Handler) as httpd:
    print("Serving on port 5000")
    httpd.serve_forever()
