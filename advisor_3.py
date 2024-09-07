import pandas as pd


def dory_advisor(portfolio, date):
    """
    Dory advisor recommends actions based on historical stock data for a specific date. Dory recommends buying the stock
    with the highest positive change, otherwise, sell the other stocks if the user has investments in them.

    Parameters:
        portfolio (dict): a dictionary where keys are stock tickers and values are amounts of stocks
        date (str): the date for which the recommendation is needed in 'YYYY-MM-DD' format

    Returns:
        dict: a dictionary with recommendations for each ticker in the portfolio, including previous values
    """
    recommendations = {}

    tickers = [ticker for ticker in portfolio if ticker != 'Cash']

    try:
        data = pd.read_csv("data.csv")
        data['date'] = pd.to_datetime(data['date'])  # ensure date column is datetime
    except FileNotFoundError:
        raise FileNotFoundError("Historical data file not found.")
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")

    portfolio_usd = portfolio['Cash']
    progression_dict = {'Cash': 0}  # stores the percentage changes for each ticker

    # loop through each ticker and calculate the change percentage
    for ticker in tickers:
        date_data = data[(data['date'] == pd.to_datetime(date)) & (data['ticker'] == ticker)]
        if date_data.empty:
            raise ValueError(f"No data available for {ticker} on {date}. The market might be closed on that day.")

        open_value = date_data['open'].values[0]
        close_value = date_data['close'].values[0]

        change = round(float(((close_value - open_value) / open_value) * 100), 3)  # calculate the percentage change
        portfolio_usd += portfolio[ticker] * close_value  # update total portfolio value in USD
        progression_dict[ticker] = change


    # find the ticker(s) with the maximum change
    max_change = max(progression_dict.values())
    max_tickers = [ticker for ticker, change in progression_dict.items() if change == max_change]

    if len(max_tickers) > 1:
        # check if 'Cash' is one of the tickers with the maximum change
        if 'Cash' in max_tickers:
            profit_ticker = 'Cash'
        else:
            # if 'Cash' is not in the list, default to the first ticker in the list
            profit_ticker = max_tickers[0]
    else:
        # if there is only one ticker with the maximum change, select it
        profit_ticker = max_tickers[0]

    if profit_ticker == 'Cash':
        recommendations['Cash'] = portfolio['Cash']
    else:
        close_value = data[(data['date'] == pd.to_datetime(date)) & (data['ticker'] == profit_ticker)]['close'].values[0]
        recommendations['Cash'] = portfolio['Cash']
        recommendation_state = "Buy"
        how_much = float((portfolio_usd / close_value) - portfolio[profit_ticker])
        recommendations[profit_ticker] = [float(portfolio[profit_ticker]), recommendation_state, float(how_much)]

    # generate recommendations for other tickers
    for ticker in tickers:
        if ticker != profit_ticker:
            if portfolio[ticker] == 0:
                recommendation_state = "Do Nothing"
                recommendations[ticker] = [float(portfolio[ticker]), recommendation_state]
            else:
                recommendation_state = "Sell"
                how_much = float(portfolio[ticker])
                recommendations[ticker] = [float(portfolio[ticker]), recommendation_state, float(how_much)]

    return recommendations

'''
# this if for debugging

# example usage:
date = "2024-07-12"

portfolio = {'Cash': 976.73, 'AAPL': 0.0, 'NVDA': 0.0}

print(dory_advisor(portfolio, date))
'''
