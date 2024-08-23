import smtplib
from email.message import EmailMessage
from datetime import datetime
import time
from config import EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT, SETTINGS_FILE_PATH


def send_email(recipient_email):
    # Create the email message
    msg = EmailMessage()
    msg.set_content("Hello")
    msg["Subject"] = "Automated Email"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient_email

    # Send the email
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)


def main():
    while True:
        # Read the settings from the file
        with open(SETTINGS_FILE_PATH, "r") as file:
            lines = file.readlines()
            email = lines[0].strip()
            email_time = datetime.strptime(lines[2].strip(), "%H:%M:%S").time()

        now = datetime.now().time()
        # Check if the current time matches the email time
        if now.hour == email_time.hour and now.minute == email_time.minute:
            send_email(email)
            # Wait for a minute before checking again to avoid multiple sends
            time.sleep(60)
        # Wait for 30 seconds before checking the time again
        time.sleep(30)


if __name__ == "__main__":
    main()
