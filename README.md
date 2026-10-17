# StockAdvisor

A comprehensive stock portfolio simulation and advisory tool built with Streamlit. This application allows users to simulate different investment strategies using historical stock data, compare advisor recommendations, and receive automated email reports.

## Features

- **Historical Data Fetching**: Automatically retrieves stock data from Financial Modeling Prep API
- **Multiple Advisors**: Three distinct investment strategies:
  - **Always Cash**: Sells all stock positions to maintain cash
  - **Always Hold**: Maintains existing positions without changes
  - **Dory**: Dynamically buys the stock with the highest daily gain and sells others
- **Portfolio Simulation**: Backtest strategies over custom time periods
- **Interactive Dashboard**: Streamlit-based UI for easy parameter configuration
- **Email Automation**: Automated daily reports with performance charts
- **Tax and Commission Inputs** (live mode only): collected with the simulation parameters, but the simulation engine
  does not apply them yet, so the public demo doesn't show them
- **Public Demo Mode**: Runs on bundled historical data with no API keys, no external requests and no emails
- **Optional Guided Tour**: A spotlight tour on desktop and a simple step-by-step walkthrough on narrow screens

## Live Demo (demo mode)

By default the app runs in **demo mode**: it uses the historical daily prices for AAPL and NVDA bundled in `data.csv`
(2023-01-03 to 2024-09-05) and the original simulation engine. Results are simulations on past data, not live market
information or investment advice. Demo mode makes no API requests, never sends emails, keeps every visitor's inputs and
results in their own session (in a private temporary folder) and never writes to the repository's files.

Streamlit Community Cloud settings: branch `stockadvisor-public-demo`, main file `main.py`, Python 3.12, no secrets.

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd StockAdvisor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Live mode (optional, private use only). Credentials are never stored in the code. Copy
   `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` (git-ignored), or set environment variables:
   - `STOCKADVISOR_MODE = "live"` and `FMP_API_KEY` from [Financial Modeling Prep](https://financialmodelingprep.com/)
     to fetch live data
   - `EMAIL_ADDRESS` and `EMAIL_PASSWORD` (a Gmail app password) for the `to_email.py` automation script

   Without these settings the app runs in demo mode.

## Usage

### Running the Application

Start the Streamlit app:
```bash
streamlit run main.py
```

### Basic Workflow

1. **Input Stock Tickers**: Enter comma-separated stock symbols (e.g., "AAPL,MSFT,NVDA")
2. **Set Date Range**: Define historical data period for analysis
3. **Configure Portfolio**: Set initial portfolio value and allocations
4. **Select Advisors**: Choose which investment strategies to simulate
5. **Run Simulation**: Execute backtesting and view results

### Advisors Explained

#### Always Cash Advisor
- **Strategy**: Immediately sells all stock positions
- **Use Case**: Risk-averse approach, prioritizes capital preservation
- **Performance**: Typically lower returns but minimal volatility

#### Always Hold Advisor
- **Strategy**: Maintains existing portfolio allocations
- **Use Case**: Buy-and-hold investment philosophy
- **Performance**: Mirrors market performance with holding costs

#### Dory Advisor
- **Strategy**: Daily analysis of price movements
  - Identifies stock with highest intraday gain
  - Invests entire portfolio in that stock
  - Sells all other positions
- **Use Case**: Momentum-based trading strategy
- **Performance**: High volatility, potential for significant gains/losses

### Email Automation

Configure automated reporting:
- Set calculation and email times
- Define simulation parameters
- Enable/disable automation status
- Receive daily performance summaries with charts

## Configuration

### API and Email Credentials
`config.py` reads `FMP_API_KEY`, `EMAIL_ADDRESS` and `EMAIL_PASSWORD` from environment variables or Streamlit secrets
(see `.streamlit/secrets.toml.example`). Never put credentials in `config.py`.

### Default Times
```python
DEFAULT_CALCULATION_TIME = time(17, 0)  # 5:00 PM
DEFAULT_EMAIL_TIME = time(19, 0)        # 7:00 PM
```

## Dependencies

Key packages include:
- `streamlit`: Web application framework
- `pandas`: Data manipulation and analysis
- `matplotlib`/`plotly`: Data visualization
- `requests`: API communication
- `smtplib`: Email functionality

See `requirements.txt` for the complete list (tested with Python 3.12).

## Tests

```bash
pip install -r requirements.txt pytest playwright
playwright install chromium   # browser tests for the guided tour; skipped if not installed
python -m pytest tests
```

## Project Structure

```
StockAdvisor/
├── main.py                 # Main Streamlit application
├── simulator.py           # Core simulation engine
├── data_fetcher.py        # Stock data retrieval
├── advisor_1.py           # Always Cash strategy
├── advisor_2.py           # Always Hold strategy
├── advisor_3.py           # Dory strategy
├── helper_functions.py    # Utility functions
├── config.py             # Configuration settings
├── to_email.py           # Email automation
├── demo_tour.py          # Optional guided tour for the public demo
├── ui.py                 # Layout helpers for the Simulator page (summary, allocation bar, labels)
├── requirements.txt      # Python dependencies
├── email_settings.example.json  # Example email settings (email_settings.json is created in live mode, git-ignored)
├── tests/                # Streamlit AppTest checks for demo mode
├── parameters.json       # Simulation parameters storage
└── data.csv             # Historical stock data cache
```

## Simulation Parameters

- **Initial Portfolio Value**: Starting capital amount
- **Commission per Trade**: Trading fee per transaction
- **Tax Rates**: Short-term and long-term capital gains taxes
- **Simulation Periods**: Time frames for backtesting (in weeks)
- **Portfolio Allocations**: Percentage distribution across assets

## Output Files

Simulation results are saved as CSV files:
- `simulation_results_1.csv`, `simulation_results_2.csv`, etc.
- Contains portfolio values, recommendations, and performance metrics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source. Please check the license file for details.

## Disclaimer

This tool is for educational and simulation purposes only. Not intended as financial advice. Past performance does not guarantee future results. Always consult with financial professionals before making investment decisions.

