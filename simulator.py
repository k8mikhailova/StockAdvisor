import pandas as pd
from datetime import datetime, timedelta
from data_fetcher import fetch_historical_data_and_save
from advisor_1 import always_cash_advisor
from advisor_2 import always_hold_advisor
from advisor_3 import dory_advisor


def is_open(date):
    """
    Check if the market is open on a specific date by checking the availability of data in the csv file

    Parameters:
        date (str): the date to check in 'YYYY-MM-DD' format

    Returns:
        bool: True if data is available for the date (market is open), False otherwise (market is closed)
    """
    date = pd.to_datetime(date)

    # fetch historical data for the given date
    try:
        # load the historical data
        data = pd.read_csv("data.csv")
        data['date'] = pd.to_datetime(data['date'])  # ensure date column is datetime

        # check if there's data for the specified date
        date_data = data[data['date'] == date]

        return not date_data.empty  # return True if data exists, False otherwise

    except FileNotFoundError:
        print("Historical data file not found")
        return False
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return False


def get_portfolio_shares(start_date, portfolio_allocations, portfolio_value):
    """
    Converts portfolio allocations into shares using historical data. If historical data for the start_date is missing,
    uses the last available data before the start_date

    Parameters:
        start_date (str): the start date for the simulation in 'YYYY-MM-DD' format
        portfolio_allocations (dict): a dictionary where keys are tickers and values are percentages of the portfolio
        portfolio_value (float): the total value of the portfolio

    Returns:
        dict: a dictionary where keys are tickers and values are amounts of shares
    """
    # convert start_date to datetime
    start_date = pd.to_datetime(start_date)

    # load the historical data
    historical_data = pd.read_csv("data.csv")
    historical_data['date'] = pd.to_datetime(historical_data['date'])  # ensure date column is datetime

    # convert percentages to USD
    portfolio_usd = {ticker: (percentage / 100) * portfolio_value for ticker, percentage in
                     portfolio_allocations.items()}

    # convert USD to shares
    portfolio_shares = {}
    for ticker, usd_value in portfolio_usd.items():
        if ticker == "Cash":
            portfolio_shares[ticker] = round(usd_value, 3)
        else:
            # get data for the start date or the most recent available date before it
            relevant_data = historical_data[
                (historical_data['ticker'] == ticker) & (historical_data['date'] <= start_date)]
            if relevant_data.empty:
                raise ValueError(f"No historical data available for {ticker} before {start_date}.")

            # get the most recent data before or on the start_date
            most_recent_data = relevant_data.sort_values(by='date', ascending=False).iloc[0]
            closing_price = most_recent_data['close']
            # format to three decimal places
            portfolio_shares[ticker] = round(float(usd_value / closing_price), 3)

    return portfolio_shares


def rec_calculations(date, rec):
    """
    Processes advisor recommendations and updates the portfolio

    Parameters:
        date (str): the date for the recommendation
        rec (dict): a dictionary with recommendations for each ticker

    Returns:
        tuple: a tuple containing the updated portfolio and the total portfolio value in USD
    """

    # retrieve historical data to get the close value
    try:
        data = pd.read_csv("data.csv")
        data['date'] = pd.to_datetime(data['date'])
    except FileNotFoundError:
        raise FileNotFoundError("Historical data file not found.")
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")

    portfolio_value_usd = 0
    cash = rec.get("Cash", 0)
    new_portfolio = {"Cash": cash}

    for ticker, value in rec.items():
        if ticker == 'Cash':
            continue

        date_data = data[(data['date'] == pd.to_datetime(date)) & (data['ticker'] == ticker)]
        if date_data.empty:
            print(f"No data found for ticker {ticker} on {date}")
            continue

        close_value = date_data['close'].values[0]

        if value[1].lower() == 'do nothing':
            new_portfolio[ticker] = round(value[0], 3)
            portfolio_value_usd += value[0] * close_value

        elif value[1].lower() == 'buy':
            new_shares = value[0] + value[2]
            portfolio_value_usd += new_shares * close_value
            cash -= value[2] * close_value
            new_portfolio[ticker] = round(new_shares, 3)

        elif value[1].lower() == 'sell':
            remaining_shares = value[0] - value[2]
            cash += value[2] * close_value
            portfolio_value_usd += remaining_shares * close_value
            new_portfolio[ticker] = round(remaining_shares, 3)

        elif value[1].lower() == 'hold':
            new_portfolio[ticker] = round(value[0], 3)
            portfolio_value_usd += value[0] * close_value

        elif value[1].lower() == 'limit buy':
            # Implement later
            pass

    new_portfolio['Cash'] = float(round(cash, 2))
    portfolio_value_usd += cash  # add cash to the total portfolio value
    portfolio_value_usd = float(round(portfolio_value_usd, 2))

    return new_portfolio, portfolio_value_usd


def get_csv(tickers_list, historical_start_date, historical_end_date, simulation_start_date, simulation_end_date,
            portfolio_value, portfolio_allocations, advisors_list, csv_path):
    """
    Runs the simulation and saves the results to a csv file

    Parameters:
        tickers_list (list): a list of tickers
        historical_start_date (str): the start date of data fetching
        historical_end_date (str): the end date of data fetching
        simulation_start_date (str): the start date of the simulation
        simulation_end_date (str): the end date of the simulation
        portfolio_value (float): the initial value of the portfolio
        portfolio_allocations (dict): initial allocations of the portfolio
        advisors_list (list): list of advisor functions to use

    Returns:
        str: the path to the generated csv file
    """
    fetch_historical_data_and_save(historical_start_date, historical_end_date, tickers_list)
    all_results = []
    historical_data = pd.read_csv("data.csv")
    historical_data['date'] = pd.to_datetime(historical_data['date'])

    for advisor in advisors_list:
        portfolio = get_portfolio_shares(simulation_start_date, portfolio_allocations, portfolio_value)
        portfolio_value_usd = portfolio_value

        # initialize the result with the initial portfolio state
        initial_result = {'Date': simulation_start_date, 'Advisor': 'Initial', 'Portfolio Value USD': portfolio_value,
                          'Cash': portfolio['Cash'], **portfolio}

        # fetch closing prices for the initial date
        date_data = historical_data[historical_data['date'] == pd.to_datetime(simulation_start_date)]
        for ticker in tickers_list:
            ticker_data = date_data[date_data['ticker'] == ticker]
            if not ticker_data.empty:
                close_price = ticker_data['close'].values[0]
                total_value = float(round(portfolio[ticker] * close_price, 3))
                initial_result.update({f'{ticker} close': close_price, f'{ticker} total': total_value})
            else:
                initial_result.update({f'{ticker} close': None, f'{ticker} total': None})

        all_results.append(initial_result)
        previous_result = initial_result.copy()

        for single_date in pd.date_range(start=simulation_start_date, end=simulation_end_date):
            date_str = single_date.strftime('%Y-%m-%d')
            result = {
                'Date': date_str,
                'Advisor': advisor
            }

            if is_open(date_str):
                rec = globals()[f"{advisor}_advisor"](portfolio, date_str)
                portfolio, portfolio_value_usd = rec_calculations(date_str, rec)
                date_data = historical_data[historical_data['date'] == pd.to_datetime(date_str)]
                result.update({'Portfolio Value USD': portfolio_value_usd})

                for ticker in tickers_list:
                    ticker_data = date_data[date_data['ticker'] == ticker]
                    if not ticker_data.empty:
                        result.update({ticker: portfolio[ticker]})
                        result.update({ticker+' close': ticker_data['close'].values[0]})
                        total = float(round(ticker_data['close'].values[0] * portfolio[ticker], 3))
                        result.update({ticker+' total': total})
                        result.update({'Cash': portfolio['Cash']})
                previous_result = result
                all_results.append(result)
            else:
                result = previous_result.copy()
                result['Date'] = date_str
                all_results.append(result)

    df = pd.DataFrame(all_results)
    df.to_csv(csv_path, index=False)


'''
# this is for debugging

tickers_list = ["AAPL", "NVDA"]
historical_start_date = "2024-07-10"
historical_end_date = "2024-07-18"
simulation_start_date = "2024-07-10"
simulation_end_date = "2024-07-18"
portfolio_value = 1000
portfolio_allocations = {'Cash': 0, 'AAPL': 50, 'NVDA': 50}
advisors_list = ['always_cash', 'always_hold']

csv_path = "simulation_results.csv"
get_csv(tickers_list, historical_start_date, historical_end_date, simulation_start_date, simulation_end_date, portfolio_value, portfolio_allocations, advisors_list, csv_path)

simulation_start_date = "2024-07-10"
simulation_end_date = "2024-07-18"
#rec = {'Cash': 500.0, 'AAPL': [0.92, 'Sell', 0.92], 'NVDA': [2.75, 'Sell', 2.75]}

print(rec_calculations(simulation_start_date, rec))
'''

