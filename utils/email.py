# utils/email_alerts.py
import smtplib
from email.mime.text import MIMEText
import os

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_new_device_alert(email, device, browser, location):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return

    html = f"""
    <html>
      <body style="background:#0d0d0d;color:#fff;font-family:Arial;padding:20px">
        <div style="max-width:480px;margin:auto;background:#1a1a1a;border-radius:12px;padding:20px">
          <h2 style="color:#8B5CF6">New Login Detected</h2>
          <p>A new device just logged into your GHost AI account.</p>
          <ul>
            <li><b>Device:</b> {device}</li>
            <li><b>Browser:</b> {browser}</li>
            <li><b>Location:</b> {location}</li>
          </ul>
          <p>If this wasn't you, please reset your password immediately.</p>
        </div>
      </body>
    </html>
    """

    msg = MIMEText(html, "html")
    msg["Subject"] = "🔐 GHost AI – New Device Login"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        s.sendmail(EMAIL_ADDRESS, email, msg.as_string())
        
def send_new_device_alert(email, device, browser, location):
    print(
        f"[SECURITY ALERT] New login\n"
        f"Email: {email}\n"
        f"Device: {device}\n"
        f"Browser: {browser}\n"
        f"Location: {location}"
    )