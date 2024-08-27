from config import API_KEY
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st
import pandas as pd


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