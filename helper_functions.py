from config import API_KEY
import requests
import matplotlib.pyplot as plt
import plotly.express as px
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

    # generate and display the summary table
    summary_df = summarize_portfolio(csv_path)
    summary_df_formatted = summary_df.round(3)
    st.markdown("<h3 style='font-size: 18px;'>Summary of Portfolio Performance</h3>", unsafe_allow_html=True)
    st.write(summary_df_formatted)

    # format the DataFrame for display with up to 3 decimal places
    df_formatted = df.round(3)

    # display the original dataframe as a table inside an expander
    with st.expander("View Original Data"):
        st.write(df_formatted)


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


def load_json_file(file_path):
    """Load data from a JSON file."""
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return {}
    except json.JSONDecodeError:
        print(f"Error decoding JSON from file: {file_path}")
        return {}


def read_and_display(display_area):
    """Reads settings from the JSON files and displays them in the specified area."""
    settings = load_json_file(SETTINGS_FILE_PATH)
    parameters = load_json_file(PARAMETERS_FILE_PATH)

    status = settings.get("status", "").lower()
    email = settings.get("email", "")
    calculations_time_str = settings.get("calculations_time", "")
    email_time_str = settings.get("email_time", "")

    if status == "active":
        time_format = "%H:%M:%S"
        calculations_time = datetime.strptime(calculations_time_str, time_format).time()
        email_time = datetime.strptime(email_time_str, time_format).time()

        # extract additional information from parameters.json
        tickers_list = parameters.get("tickers", [])
        start_date = parameters.get("start_date", "")
        end_date = parameters.get("end_date", "")
        portfolio_value = parameters.get("portfolio_value", 1000)
        periods = parameters.get("periods", [])
        commission_per_trade = parameters.get("commission_per_trade", 0)
        include_tax = parameters.get("tax", False)
        short_term_capital_gains_tax_rate = parameters.get("short_term_capital_gains_tax_rate", 0)
        long_term_capital_gains_tax_rate = parameters.get("long_term_capital_gains_tax_rate", 0)
        portfolio_allocations = parameters.get("portfolio_allocations", {})
        selected_advisors = parameters.get("advisors", [])

        # convert periods to strings
        periods_str = [str(period) for period in periods]

        # Create markdown content
        content = (
            f"**Current Email:** {email}<br>"
            f"**Positions and balances will be calculated at:** {calculations_time.strftime('%I:%M %p')}<br>"
            f"**You will be emailed at:** {email_time.strftime('%I:%M %p')}<br><br>"
            f"**Tickers:** {', '.join(tickers_list)}<br>"
            f"**Simulation Start Date:** {start_date}<br>"
            f"**Simulation End Date:** {end_date}<br>"
            f"**Periods:** {', '.join(periods_str)} weeks<br>"
            f"**Portfolio Value:** ${portfolio_value:}<br>"
            f"**Commission per trade:** {commission_per_trade:}<br>"
            f"**Tax Included:** {'Yes' if include_tax else 'No'}<br>"
            f"**Short Term Capital Gains Tax Rate:** {short_term_capital_gains_tax_rate:.2f}%<br>"
            f"**Long Term Capital Gains Tax Rate:** {long_term_capital_gains_tax_rate:.2f}%<br>"
            f"**Portfolio Allocations:** {portfolio_allocations}<br>"
            f"**Selected Advisors:** {', '.join(selected_advisors)}"
        )

        # Display information from both files
        display_area.empty()
        display_area.markdown(content, unsafe_allow_html=True)
    elif status == "paused":
        display_area.empty()
        display_area.write("Automation is paused. Set to active to resume.")
    else:
        display_area.empty()
        display_area.write("No active settings found.")


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
                   periods, initial_value, allocations, commission_per_trade, include_tax, short_term_capital_gains, long_term_capital_gains, selected_advisors):
    '''
    Generates csv files and creates png images of plots.
    return: a list of png file names
    '''

    # generate the next csv file name based on the file index
    file_index = 0

    png_files = []
    csv_files = []
    period_labels = []

    # check if simulation start and end dates are provided
    if simulation_start_date and simulation_end_date:
        file_index += 1
        csv_path = f"simulation_results_{file_index}.csv"
        get_csv(tickers_list, start_date, end_date, simulation_start_date, simulation_end_date, initial_value,
                allocations, commission_per_trade, include_tax, short_term_capital_gains, long_term_capital_gains, selected_advisors, csv_path)
        save_path = "plot_1.png"
        period_label = f"From {simulation_start_date} to {simulation_end_date}"
        plot_graphs(selected_advisors, csv_path, save_path, period_label=period_label)
        png_files.append(save_path)
        csv_files.append(csv_path)
        period_labels.append(period_label)

    # check if simulation periods are provided
    if periods:
        today = date.today()

        for period in periods:
            file_index += 1
            period_start_date = today - timedelta(weeks=period)
            period_end_date = today

            # convert to strings (e.g., "YYYY-MM-DD")
            period_start_date_str = period_start_date.strftime("%Y-%m-%d")
            period_end_date_str = period_end_date.strftime("%Y-%m-%d")

            # overwrite csv file
            csv_path = f"simulation_results_{file_index}.csv"
            get_csv(tickers_list, start_date, end_date, period_start_date_str, period_end_date_str, initial_value,
                    allocations, commission_per_trade, include_tax, short_term_capital_gains, long_term_capital_gains,
                    selected_advisors, csv_path)
            save_path = f"plot_{file_index}.png"
            period_label = f"Period: {period} Weeks"
            plot_graphs(selected_advisors, csv_path, save_path, period_label=period_label)
            png_files.append(save_path)
            csv_files.append(csv_path)
            period_labels.append(period_label)

    # return a dictionary with 'png' and 'csv' keys
    return {
        'png': png_files,
        'csv': csv_files,
        'period_labels': period_labels
    }


def summarize_portfolio(csv_file):
    # read the csv file into a DataFrame
    df = pd.read_csv(csv_file)

    # extract tickers from the column names
    tickers = [col.split()[0] for col in df.columns if 'total' in col]

    # initialize an empty list to store the results
    summary_data = []

    # group the data by Advisor
    grouped = df.groupby('Advisor')

    # iterate over each group (advisor)
    for advisor, group, in grouped:
        # get the initial and final portfolio values
        initial_value = group.iloc[0]['Portfolio Value USD']
        final_value = group.iloc[-1]['Portfolio Value USD']

        # calculate the percentage return
        percent_return = round(((final_value - initial_value) / initial_value) * 100, 2)

        # calculate the total for each ticker on the last day
        ticker_totals = {f'{ticker} total': group.iloc[-1][f'{ticker} total'] for ticker in tickers}

        # append the results to the summary_data list
        summary_data.append({
            'Advisor': advisor,
            'Final Portfolio Value': final_value,
            '% Return': percent_return,
            **ticker_totals
        })

    # convert the summary_data list into a DataFrame
    summary_df = pd.DataFrame(summary_data)

    return summary_df


def create_summary_html(csv_file):
    ''' this function is used as an addition to summarize portfolio function and is used for emailing'''
    # call summarize_portfolio to get the summary DataFrame
    summary_df = summarize_portfolio(csv_file)

    # convert the DataFrame to an HTML table
    table_html = summary_df.to_html(classes='table table-bordered', index=False)

    # return the HTML table
    return table_html


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


'''
# Example usage of summarize_portfolio function
csv_file = 'simulation_results_3.csv'
summary_df = summarize_portfolio(csv_file)
print(summary_df)
'''



