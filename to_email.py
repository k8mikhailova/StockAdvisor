import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email import encoders
import os
from datetime import datetime
import time
import json
import pandas as pd
from config import EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT, SETTINGS_FILE_PATH
from helper_functions import run_simulation, create_summary_html


def send_email(recipient_email, png_csv_dict):
    try:
        # create the email message
        msg = generate_email_content(recipient_email, png_csv_dict)

        # send the email
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print("Email sent")
    except Exception as e:
        print("Failed to send email:", e)


def generate_email_content(recipient_email, png_csv_dict):
    # create the email content
    msg = MIMEMultipart("related")
    msg["Subject"] = "Daily Reports from StockAdvisor"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient_email

    # create the email body with HTML
    html_content = """
        <html>
        <body>
            <p>Hello,</p>
            <p>Here’s your daily report from StockAdvisor, featuring the latest stock market performance based on the periods you've tracked.</p>
        """

    image_parts = []

    # iterate over the PNG and CSV file paths
    for png_path, csv_path in zip(png_csv_dict['png'], png_csv_dict['csv']):
        if os.path.isfile(png_path):  # check if PNG path is a file
            try:
                # attach the PNG image to the email body
                with open(png_path, "rb") as f:
                    img_data = f.read()
                    img_type = os.path.splitext(png_path)[1][1:]  # get image file type (e.g., 'png')
                    img_name = os.path.basename(png_path)

                    # create an image MIME part
                    img_part = MIMEImage(img_data, _subtype=img_type)
                    img_part.add_header("Content-ID", f"<{img_name}>")
                    img_part.add_header("Content-Disposition", "inline", filename=img_name)
                    image_parts.append(img_part)

                    # add the image to the HTML content
                    html_content += f'<img src="cid:{img_name}" alt="{img_name}"><br>'

                    print(f"Added image: {png_path}")

            except Exception as e:
                print(f"Failed to include {png_path} in the email body: {e}")

        if os.path.isfile(csv_path):  # Check if CSV path is a file
            try:
                # Generate the summary HTML table
                table_html = create_summary_html(csv_path)

                # Add the HTML table to the email content
                html_content += f'<h3>Summary of Portfolio Performance</h3>{table_html}<br>'

            except Exception as e:
                print(f"Failed to include {csv_path} in the email body: {e}")

    # add the closing content
    html_content += """
            <p>For a more detailed analysis or to adjust your tracked periods, please log in to StockAdvisor.</p>
        </body>
        </html>
    """

    # attach the HTML content to the email
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    # Attach all image parts after the HTML content
    for img_part in image_parts:
        msg.attach(img_part)

    return msg


def is_automation_active():
    """Check if automation is active based on the JSON settings file."""
    try:
        with open(SETTINGS_FILE_PATH, "r") as file:
            settings = json.load(file)
        return settings.get("status", "").lower() == "active"  # true or false
    except FileNotFoundError:
        # control file does not exist, default to inactive
        return False


def load_parameters():
    """Load parameters from parameters.json."""
    try:
        with open("parameters.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print("Parameters file not found.")
        return {}


def main():
    png_csv_dict = {}

    while True:
        # check if automation is active
        if is_automation_active():
            # read the settings from the JSON file
            try:
                with open(SETTINGS_FILE_PATH, "r") as file:
                    settings = json.load(file)
                    email = settings.get("email", "")
                    email_time_str = settings.get("email_time", "00:00:00")
                    calculations_time_str = settings.get("calculations_time", "00:00:00")

                    if not email_time_str or not calculations_time_str:
                        print("Error: Missing time settings in the settings file.")
                        time.sleep(30)
                        continue

                # convert time strings to time objects
                calculations_time = datetime.strptime(calculations_time_str, "%H:%M:%S").time()
                email_time = datetime.strptime(email_time_str, "%H:%M:%S").time()

                now = datetime.now().time()

                # check if the current time matches the calculations time
                if now.hour == calculations_time.hour and now.minute == calculations_time.minute:
                    parameters = load_parameters()

                    if parameters:
                        # extract parameters for run_simulation
                        tickers_list = parameters.get("tickers", [])
                        start_date = parameters.get("start_date", "")
                        end_date = parameters.get("end_date", "")
                        simulation_start_date = parameters.get("simulation_start_date", "")
                        simulation_end_date = parameters.get("simulation_end_date", "")
                        periods = parameters.get("periods", [])
                        initial_value = parameters.get("portfolio_value", 1000)
                        commission_per_trade = parameters.get("commisson_per_trade", 0)
                        include_tax = parameters.get("tax", False)
                        short_term_capital_gains = parameters.get("short_term_capital_gains_tax_rate", 0)
                        long_term_capital_gains = parameters.get("long_term_capital_gains_tax_rate", 0)
                        allocations = parameters.get("portfolio_allocations", {})
                        selected_advisors = parameters.get("advisors", [])

                        png_csv_dict = run_simulation(tickers_list, start_date, end_date, simulation_start_date,
                                                  simulation_end_date, periods, initial_value, allocations, commission_per_trade,
                                                  include_tax, short_term_capital_gains, long_term_capital_gains, selected_advisors)
                        print(png_csv_dict)
                        print("Simulation executed.")

                    # wait for a minute before checking again to avoid multiple executions
                    time.sleep(60)

                # check if the current time matches the email time
                if now.hour == email_time.hour and now.minute == email_time.minute:
                    send_email(email, png_csv_dict)
                    # wait for a minute before checking again to avoid multiple sends
                    time.sleep(60)

            except Exception as e:
                print("Error reading settings or sending email:", e)

        # wait for 30 seconds before checking the time again
        time.sleep(30)


if __name__ == "__main__":
    main()


