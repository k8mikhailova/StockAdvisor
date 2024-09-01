from config import API_KEY
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import json
from config import SETTINGS_FILE_PATH, PARAMETERS_FILE_PATH
from simulator import get_csv


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


def plot_graphs(selected_advisors, csv_path, save_path=None, period_label=None):
    """
        Plot the simulation results without displaying tables and save image (used for emailing)

        Parameters:
        - selected_advisors: List of advisors to include in the plot
        - csv_path: Path to the CSV file containing simulation data
        - save_path: Path to save the plot image. If None, the plot will not be saved
        - period_label: Optional label for the plot title
        """
    # load the csv file into a dataframe
    df = pd.read_csv(csv_path)

    # convert date column to datetime
    df['Date'] = pd.to_datetime(df['Date']).dt.date  # Convert to date only

    # create a figure for the plot
    plt.figure(figsize=(10, 6))

    # plot the portfolio value vs time for each advisor
    for advisor in selected_advisors:
        advisor_df = df[df['Advisor'] == advisor]
        plt.plot(advisor_df['Date'], advisor_df['Portfolio Value USD'], label=advisor)

    # labeling the plot
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
    step = max(1, len(date_range) // 10)  # Adjust step to control the number of labels
    plt.xticks(date_range[::step], rotation=45)

    # save the plot as an image file if save_path is provided
    if save_path:
        plt.savefig(save_path)
    else:
        plt.show()

    # close the plot to free memory
    plt.close()


def read_and_display(file_path, display_area):
    """Reads settings from the JSON file and displays them in the specified area."""
    try:
        with open(file_path, "r") as file:
            settings = json.load(file)

        status = settings.get("status")
        email = settings.get("email", "")
        calculations_time_str = settings.get("calculations_time", "")
        email_time_str = settings.get("email_time", "")

        if status.lower() == "active":
            time_format = "%H:%M:%S"
            calculations_time = datetime.strptime(calculations_time_str, time_format).time()
            email_time = datetime.strptime(email_time_str, time_format).time()

            display_area.empty()
            display_area.markdown(
                f"**Current Email:** {email}<br>"
                f"**Positions and balances will be calculated at:** {calculations_time.strftime('%I:%M %p')}<br>"
                f"**You will be emailed at:** {email_time.strftime('%I:%M %p')}",
                unsafe_allow_html=True
            )
        elif status.lower() == "paused":
            display_area.empty()
            display_area.write("Automation is paused. Set to active to resume.")
    except FileNotFoundError:
        display_area.empty()
        display_area.write("No settings file found.")


def save_email_settings(email, calculations_time, email_time, status):
    """Saves the settings to the JSON file."""
    settings = {
        "email": email,
        "calculations_time": calculations_time.strftime('%H:%M:%S') if status == "Active" else "",
        "email_time": email_time.strftime('%H:%M:%S') if status == "Active" else "",
        "status": status
    }

    with open(SETTINGS_FILE_PATH, "w") as file:
        json.dump(settings, file, indent=4)


def save_email_parameters(tickers, start_date, end_date, sim_start_date, sim_end_date, periods, portfolio_value,
                          commission, tax, short_cap_gains, long_cap_gains, portfolio_allocations, advisors):
    """Saves the settings to the JSON file."""
    # convert dates to strings, handle NoneType
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    sim_start_date_str = sim_start_date.strftime('%Y-%m-%d') if sim_start_date else ""
    sim_end_date_str = sim_end_date.strftime('%Y-%m-%d') if sim_end_date else ""

    parameters = {
        "tickers": tickers,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "simulation_start_date": sim_start_date_str,
        "simulation_end_date": sim_end_date_str,
        "periods": periods,
        "portfolio_value": portfolio_value,
        "commisson_per_trade": commission,
        "tax": tax,
        "short_term_capital_gains_tax_rate": short_cap_gains,
        "long_term_capital_gains_tax_rate": long_cap_gains,
        "portfolio_allocations": portfolio_allocations,
        "advisors": advisors
    }

    with open(PARAMETERS_FILE_PATH, "w") as file:
        json.dump(parameters, file, indent=4)


def run_simulation(tickers_list, start_date, end_date, simulation_start_date, simulation_end_date,
                   periods, initial_value, allocations, selected_advisors):
    '''
    Generates csv files and creates png images of plots.
    return: a list of png file names
    '''

    # generate the next csv file name based on the file index
    file_index = 0

    png_list = []

    # check if simulation start and end dates are provided
    if simulation_start_date and simulation_end_date:
        file_index += 1
        csv_path = f"simulation_results_{file_index}.csv"
        get_csv(tickers_list, start_date, end_date, simulation_start_date, simulation_end_date, initial_value,
                allocations, selected_advisors, csv_path)
        save_path = "plot_1.png"
        plot_graphs(selected_advisors, csv_path, save_path, period_label=f"From {simulation_start_date} to {simulation_end_date}")
        png_list.append(save_path)

    # check if simulation periods are provided
    if periods:
        today = date.today()

        for period in periods:
            file_index += 1
            period_start_date = today - timedelta(weeks=period)
            period_end_date = today

            # overwrite csv file
            csv_path = f"simulation_results_{file_index}.csv"
            get_csv(tickers_list, start_date, end_date, period_start_date, period_end_date, initial_value,
                    allocations, selected_advisors, csv_path)
            save_path = f"plot_{file_index}.png"
            plot_graphs(selected_advisors, csv_path, save_path, period_label=f"Period: {period} Weeks")
            png_list.append(save_path)

    return png_list
