def always_cash_advisor(portfolio, date=None,):
    """
    The 'always cash' advisor recommends to sell any stock the user has invested in (value > 0)
    and do nothing otherwise.

    Parameters:
      portfolio (dict): A dictionary containing portfolio allocations. Example: {"Cash": 200, "AAPL": 0, "NVDA": 3.34}
      date (str): The date for which the recommendation is needed. This parameter is ignored by this advisor.

    Returns:
      dict: A dictionary with recommendations for each portfolio item, including previous values.
            Example: {"Cash": 200, "AAPL": [0, "Do nothing"], "NVDA": [3.34, "Sell", 3.34]}
    """
    recommendations = {}
    for ticker, value in portfolio.items():
        if ticker == 'Cash':
            recommendations[ticker] = value  # Just keep the cash value without recommendation
        else:
            if value > 0:
                recommendations[ticker] = [value, "Sell", round(value, 3)]
            else:
                recommendations[ticker] = [value, "Do nothing"]
    return recommendations

"""
portfolio = {'Cash': 500, 'AAPL': 2.29}
print(always_cash_advisor(portfolio))

Output: {'Cash': 500, 'AAPL': [2.29, 'Sell', 2.29]}
"""


