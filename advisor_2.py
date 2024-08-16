def always_hold_advisor(portfolio, date=None):
    """
    The 'always hold' advisor recommends to hold the stock if the user already invested in it (value > 0)
    and do nothing otherwise.

    Parameters:
        portfolio (dict): A dictionary containing portfolio allocations. Example: {"Cash": 200, "AAPL": 0, "NVDA": 3.34}
        date (str): The date for which the recommendation is needed. This parameter is ignored by this advisor.

    Returns:
        dict: A dictionary with recommendations for each portfolio item, including previous values.
              Example: {"Cash": 200, "AAPL": [0, "Do nothing"], "NVDA": [3.34, "Hold"]}
    """
    recommendations = {}
    for ticker, value in portfolio.items():
        if ticker == "Cash":
            recommendations[ticker] = value  # Just keep the cash value without recommendation
        else:
            if value > 0:
                recommendations[ticker] = [value, "Hold"]
            else:
                recommendations[ticker] = [value, "Do nothing"]
    return recommendations


