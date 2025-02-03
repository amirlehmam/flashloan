import logging
import smtplib
from email.mime.text import MIMEText
import requests
import json

def send_email_alert(subject: str, message: str, to_email: str):
    # Configure these values with your credentials
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    from_email = "flashloan.arbitrage9@gmail.com"
    password = "Gdze_94400"  # Consider using environment variables or a secure vault!
    
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
        logging.info("Email alert sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send email alert: {e}")

def send_slack_alert(message: str, webhook_url: str):
    payload = {"text": message}
    try:
        response = requests.post(webhook_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
        if response.status_code != 200:
            logging.error(f"Slack alert failed: {response.text}")
        else:
            logging.info("Slack alert sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send Slack alert: {e}")
