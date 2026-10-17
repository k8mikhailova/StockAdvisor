import os
import requests
import pandas as pd
from config import API_KEY, HISTORICAL_DATA_PATH

_data_cache = {}


def load_historical_data(data_path=HISTORICAL_DATA_PATH):
    """
    Load the historical data csv into a DataFrame. The parsed file is cached per path and modification time, so the
    simulator does not re-read the csv for every simulated day. A copy is returned so callers cannot change the cache.
    """
    key = (os.path.abspath(data_path), os.path.getmtime(data_path))
    if key not in _data_cache:
        data = pd.read_csv(data_path)
        data['date'] = pd.to_datetime(data['date'])  # ensure date column is datetime
        _data_cache.clear()
        _data_cache[key] = data
    return _data_cache[key].copy()


def fetch_historical_data_and_save(start_date, end_date=None, tickers=None, output_path=HISTORICAL_DATA_PATH):
    """
    Fetch historical stock data from Financial Modeling Prep API for multiple tickers
    between start_date and end_date or for a single day if end_date is not provided,
    and save the results to output_path (by default 'data.csv'). Only used in live mode.

    Parameters:
        start_date (str): the start date for data collection in 'YYYY-MM-DD' format
        end_date (str, optional): the end date for data collection in 'YYYY-MM-DD' format
        tickers (list, optional): a list of stock ticker symbols
        output_path (str, optional): where to save the fetched data

    Returns:
        None
    """

    if not API_KEY:
        raise RuntimeError("FMP_API_KEY is not configured. Set it as an environment variable or Streamlit secret.")

    if end_date is None:
        end_date = pd.to_datetime(start_date) + pd.DateOffset(days=1)
    else:
        end_date = pd.to_datetime(end_date) + pd.DateOffset(days=1)  # include end date in the range

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    all_data = []

    # generate all dates in the range
    all_dates = pd.date_range(start=start_date, end=end_date - pd.DateOffset(days=1), freq='D')
    all_dates_df = pd.DataFrame({'date': all_dates})

    for ticker in tickers:
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?apikey={API_KEY}"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if 'historical' in data:
                historical_data = data['historical']
                df = pd.DataFrame(historical_data)
                df['date'] = pd.to_datetime(df['date'])
                df['ticker'] = ticker
                df = df[['date', 'ticker', 'open', 'close', 'high', 'low', 'volume']]

                # filter for the given date range
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
        result_df.to_csv(output_path, index=False)
        print(f"Data saved to {output_path} for date range: {start_date.date()} to {end_date.date()}")
    else:
        print(f"No data fetched for date range: {start_date.date()} to {end_date.date()}")

"""
# this if for debugging

start_date = "2023-05-08"
end_date = "2024-07-18"
stock = ['AAPL']
fetch_historical_data_and_save(start_date, end_date, tickers=stock)
"""