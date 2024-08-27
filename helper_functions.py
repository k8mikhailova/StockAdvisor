from config import API_KEY
import requests


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


