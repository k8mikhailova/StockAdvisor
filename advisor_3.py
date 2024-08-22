import pandas as pd


def dory_advisor(portfolio, date):
    """
    Dory advisor recommends actions based on historical stock data for a specific date. Dory recommends buying the stock
    with the highest positive change, otherwise, sell the other stocks if the user has investments in them.

    Parameters:
        portfolio (dict): A dictionary where keys are stock tickers and values are amounts of stocks.
        date (str): The date for which the recommendation is needed in 'YYYY-MM-DD' format.

    Returns:
        dict: A dictionary with recommendations for each ticker in the portfolio, including previous values.
    """
    recommendations = {}

    tickers = [ticker for ticker in portfolio if ticker != 'Cash']

    try:
        data = pd.read_csv("data.csv")
        data['date'] = pd.to_datetime(data['date'])  # Ensure date column is datetime
    except FileNotFoundError:
        raise FileNotFoundError("Historical data file not found.")
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")

    portfolio_usd = portfolio['Cash']
    progression_dict = {'Cash': 0}  # Stores the percentage changes for each ticker

    # Loop through each ticker and calculate the change percentage
    for ticker in tickers:
        date_data = data[(data['date'] == pd.to_datetime(date)) & (data['ticker'] == ticker)]
        if date_data.empty:
            raise ValueError(f"No data available for {ticker} on {date}. The market might be closed on that day.")

        open_value = date_data['open'].values[0]
        close_value = date_data['close'].values[0]

        change = ((close_value - open_value) / open_value) * 100  # Calculate the percentage change
        portfolio_usd += portfolio[ticker] * close_value  # Update total portfolio value in USD
        progression_dict[ticker] = change

    # Find the ticker(s) with the maximum change
    max_change = max(progression_dict.values())
    max_tickers = [ticker for ticker, change in progression_dict.items() if change == max_change]

    if len(max_tickers) > 1:
        # Handle the edge case where multiple tickers have the same maximum change
        max_tickers = [ticker for ticker in max_tickers if ticker != 'Cash']
        profit_ticker = max_tickers[0]  # Default to the first one if multiple are the same
    else:
        profit_ticker = max_tickers[0]

    if profit_ticker == 'Cash':
        recommendations['Cash'] = portfolio['Cash']
    else:
        close_value = data[(data['date'] == pd.to_datetime(date)) & (data['ticker'] == profit_ticker)]['close'].values[0]
        recommendations['Cash'] = 0
        recommendation_state = "Buy"
        how_much = round(float((portfolio_usd / close_value) - portfolio[ticker]), 3)
        recommendations[profit_ticker] = [float(portfolio[profit_ticker]), recommendation_state, float(how_much)]

    # Generate recommendations for other tickers
    for ticker in tickers:
        if ticker != profit_ticker:
            recommendation_state = "Sell"
            how_much = round(float(portfolio[ticker]), 3)
            recommendations[ticker] = [float(portfolio[ticker]), recommendation_state, float(how_much)]

    return recommendations

# Example usage:
date = "2024-08-13"
portfolio = {"Cash": 500, "AAPL": 3.123, "NVDA": 2.401, "MSFT": 0.23}

print(dory_advisor(portfolio, date))
