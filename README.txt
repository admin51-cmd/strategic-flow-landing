Strategic Flow Co. — Landing Page
===================================

REQUIREMENTS
------------
- Python 3.8 or higher (no extra packages needed — uses stdlib only)

ENVIRONMENT VARIABLES
---------------------
Set the following before starting the server:

  SMTP_SENDER       Your Google Workspace / Gmail sender address
                    e.g. joao@strategic-cap.com

  SMTP_RECIPIENT    The address that receives enquiry emails
                    e.g. admin51@strategic-cap.com

  GMAIL_APP_PASSWORD  The 16-character Gmail App Password for SMTP_SENDER
                      Google Account → Security → 2-Step Verification → App passwords

On Linux / macOS you can export them in your shell session:

  export SMTP_SENDER="joao@strategic-cap.com"
  export SMTP_RECIPIENT="admin51@strategic-cap.com"
  export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"

Or add them to a .env file and load them with your hosting platform's
environment-variable manager (e.g. cPanel, Heroku, Railway, etc.).

RUNNING THE SERVER
------------------
  python3 serve.py

The site will be available at http://localhost:5000

To run on a different port, edit the port number in serve.py (last line).

CONTACT FORM
------------
The form POSTs JSON to /api/contact (handled by serve.py).
Emails are sent via Gmail SMTP (smtp.gmail.com:587 with STARTTLS).

FILE STRUCTURE
--------------
  index.html              Main page (all HTML, CSS, JS in one file)
  serve.py                Python static + API server
  favicon.ico             Browser tab icon
  assets/
    fonts/                Self-hosted typefaces (URWClassico, Gadugi)
    img/                  All site images and logo

NOTES
-----
- The site requires no Node.js, no npm, no build step.
- All fonts and images are self-hosted; no external CDN is needed
  except for Google Fonts (DM Sans fallback) loaded in <head>.
- For production, consider running behind nginx or Caddy as a reverse
  proxy, and use a process manager like systemd or supervisord to keep
  serve.py alive.
