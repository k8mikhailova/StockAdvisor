from config import API_KEY
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st
import pandas as pd
import datetime


def validate_tickers(tickers):
    """
    Validate ticker symbols using the FMP API.

    Parameters:
        tickers (list): List of ticker symbols to validate.

    Returns:
        tuple: A tuple containing a list of valid tickers and a list of invalid tickers.
    """
    base_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/"
    valid_tickers = []
    invalid_tickers = []

    for ticker in tickers:
        response = requests.get(f"{base_url}/{ticker}?apikey={API_KEY}")
        if response.status_code == 200 and response.json():
            valid_tickers.append(ticker)
        else:
            invalid_tickers.append(ticker)

    return valid_tickers, invalid_tickers


def plot_simulation_results(selected_advisors, csv_path, period_label=None):
    # load the csv file into a dataframe and display it
    df = pd.read_csv(csv_path)

    # convert date column to datetime
    df['Date'] = pd.to_datetime(df['Date']).dt.date  # convert to date only

    # plot the portfolio value vs time for each advisor
    st.header(f"{period_label if period_label else ''}")
    plt.figure(figsize=(10, 6))

    for advisor in selected_advisors:
        advisor_df = df[df['Advisor'] == advisor]
        plt.plot(advisor_df['Date'], advisor_df['Portfolio Value USD'], label=advisor)

    plt.xlabel('Date')
    plt.ylabel('Portfolio Value (USD)')
    plt.title(f'{period_label if period_label else ""}')
    plt.legend()

    # format the date axis to prevent overcrowding
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))

    # set x-axis limits to start and end dates
    plt.xlim(df['Date'].min(), df['Date'].max())

    # manually set x-axis labels
    date_range = df['Date'].unique()
    step = max(1, len(date_range) // 10)  # adjust step to control the number of labels
    plt.xticks(date_range[::step], rotation=45)

    st.pyplot(plt)

    # display the dataframe as a table
    st.write(df)


def read_and_display(file_path, display_area):
    """Reads settings from the file and displays them in the specified area."""
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()
            if len(lines) >= 3 and lines[0].strip().lower() != "inactive":
                email = lines[0].strip()
                try:
                    # assume military time format with seconds
                    time_format = "%H:%M:%S"
                    calculations_time = datetime.datetime.strptime(lines[1].strip(), time_format).time()
                    email_time = datetime.datetime.strptime(lines[2].strip(), time_format).time()

                    # clear the display area and then display updated content
                    display_area.empty()
                    display_area.markdown(
                        f"**Current Email:** {email}<br>"
                        f"**Positions and balances will be calculated at:** {calculations_time.strftime('%I:%M %p')}<br>"
                        f"**You will be emailed at:** {email_time.strftime('%I:%M %p')}",
                        unsafe_allow_html=True
                    )
                except ValueError as e:
                    display_area.write(
                        f"Error reading time values: {e}. Ensure the time format is 'HH:MM:SS'.")
                    return
            else:
                display_area.empty()
                display_area.write("Automation is paused. Set to active to resume.")
    except FileNotFoundError:
        display_area.empty()
        display_area.write("No settings file found.")


def save_settings(file_path, email, calculations_time, email_time, status):
    """Saves the settings to the file."""
    with open(file_path, "w") as file:
        if status == "Active":
            file.write(f"{email}\n")
            file.write(f"{calculations_time.strftime('%H:%M:%S')}\n")  # save in military time format with seconds
            file.write(f"{email_time.strftime('%H:%M:%S')}\n")  # save in military time format with seconds
        else:
            file.write("inactive\n")