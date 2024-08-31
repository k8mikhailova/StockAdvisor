import smtplib
from email.message import EmailMessage
from datetime import datetime
import time
from config import EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT, SETTINGS_FILE_PATH


def send_email(recipient_email):
    try:
        # create the email message
        msg = EmailMessage()
        msg.set_content("Hello")
        msg["Subject"] = "Automated Email"
        msg["From"] = "StockAdvisor"
        msg["To"] = recipient_email

        # send the email
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print("Email sent")
    except Exception as e:
        print("Failed to send email")


def is_automation_active():
    # check the control file to see if automation is active
    try:
        with open(SETTINGS_FILE_PATH, "r") as file:
            status = file.readline().strip()
        return status.lower() != "inactive"
    except FileNotFoundError:
        # control file does not exist, default to inactive
        return False


def main():
    while True:
        # check if automation is active
        if is_automation_active():
            # read the settings from the file
            with open(SETTINGS_FILE_PATH, "r") as file:
                lines = file.readlines()
                email = lines[0].strip()
                email_time = datetime.strptime(lines[2].strip(), "%H:%M:%S").time()
            now = datetime.now().time()

            # check if the current time matches the email time
            if now.hour == email_time.hour and now.minute == email_time.minute:
                send_email(email)
                # wait for a minute before checking again to avoid multiple sends
                time.sleep(60)

            # wait for 30 seconds before checking the time again
            time.sleep(30)


if __name__ == "__main__":
    main()


