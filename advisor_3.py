import pandas as pd


def dory_advisor(portfolio, date):
    """
    Dory advisor recommends actions based on historical stock data for a specific date. Dory recommends buying the stock
    if the close value is greater than the open value for the same day, otherwise sell (if the user has investments in
    the stock). Dory only works with one stock.

    Parameters:
        portfolio (dict): A dictionary where keys are stock tickers and values are amounts of stocks.
        date (str): The date for which the recommendation is needed in 'YYYY-MM-DD' format.

    Returns:
        dict: A dictionary with recommendations for each ticker in the portfolio, including previous values.
    """
    recommendations = {}

    tickers = [ticker for ticker in portfolio if ticker != 'Cash']
    if len(tickers) != 1:
        raise ValueError("Dory advisor only supports one stock at a time (excluding cash).")

    stock = tickers[0]

    try:
        data = pd.read_csv("data.csv")
        data['date'] = pd.to_datetime(data['date'])  # Ensure date column is datetime
    except FileNotFoundError:
        raise FileNotFoundError("Historical data file not found.")
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")

    date_data = data[(data['date'] == pd.to_datetime(date)) & (data['ticker'] == stock)]
    if date_data.empty:
        raise ValueError(f"No data available for {stock} on {date}. The market might be closed on that day.")

    open_value = date_data['open'].values[0]
    close_value = date_data['close'].values[0]

    recommendations['Cash'] = portfolio['Cash']  # Just keep the cash value without recommendation

    if portfolio[stock] > 0:
        if close_value > open_value:
            recommendation_state = "Buy"
            how_much = round(float(portfolio['Cash'] / close_value), 3)
        else:
            recommendation_state = "Sell"
            how_much = round(float(portfolio[stock]), 3)
    else:
        if close_value > open_value:
            recommendation_state = "Buy"
            how_much = round(float(portfolio['Cash'] / close_value), 3)
        else:
            recommendation_state = "Do nothing"
            how_much = 0.0

    recommendations[stock] = [float(portfolio[stock]), recommendation_state, float(how_much)]

    return recommendations

"""
date = "2024-08-06"
portfolio = {"Cash": 500, "AAPL": 3.123}

print(dory_advisor(portfolio, date))
"""