import requests
import pandas as pd
from config import API_KEY


def fetch_historical_data_and_save(start_date, end_date=None, tickers=None):
    """
    Fetch historical stock data from Financial Modeling Prep API for multiple tickers
    between start_date and end_date or for a single day if end_date is not provided,
    and save the results to a file named 'data.csv'.

    Parameters:
        start_date (str): The start date for data collection in 'YYYY-MM-DD' format.
        end_date (str, optional): The end date for data collection in 'YYYY-MM-DD' format.
        tickers (list, optional): A list of stock ticker symbols.

    Returns:
        None
    """
    if end_date is None:
        end_date = pd.to_datetime(start_date) + pd.DateOffset(days=1)
    else:
        end_date = pd.to_datetime(end_date) + pd.DateOffset(days=1)  # Include end date in the range

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    all_data = []

    # Generate all dates in the range
    all_dates = pd.date_range(start=start_date, end=end_date - pd.DateOffset(days=1), freq='D')
    all_dates_df = pd.DataFrame({'date': all_dates})

    for ticker in tickers:
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?apikey={API_KEY}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if 'historical' in data:
                historical_data = data['historical']
                df = pd.DataFrame(historical_data)
                df['date'] = pd.to_datetime(df['date'])
                df['ticker'] = ticker
                df = df[['date', 'ticker', 'open', 'close', 'high', 'low', 'volume']]
                # Filter for the given date range
                df = df[(df['date'] >= start_date) & (df['date'] < end_date)]
                if not df.empty:
                    all_data.append(df)
                else:
                    print(f"No data available for {ticker} on {start_date.date()}.")
            else:
                print(f"No historical data found for ticker {ticker}")
        else:
            print(f"Error fetching data for ticker {ticker}: {response.status_code}")

    if all_data:
        result_df = pd.concat(all_data, ignore_index=True)
        result_df.to_csv("data.csv", index=False)
        print(f"Data saved to data.csv for date range: {start_date.date()} to {end_date.date()}")
    else:
        print(f"No data fetched for date range: {start_date.date()} to {end_date.date()}")

"""
start_date = "2023-05-08"
end_date = "2024-07-18"
stock = ['AAPL']
fetch_historical_data_and_save(start_date, end_date, tickers=stock)
"""