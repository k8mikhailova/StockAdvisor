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
- **Tax Calculations**: Optional capital gains tax considerations
- **Commission Modeling**: Realistic trading cost simulation

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

3. Set up your API key:
   - Get a free API key from [Financial Modeling Prep](https://financialmodelingprep.com/)
   - Replace the `API_KEY` in `config.py` with your key

4. Configure email settings (optional):
   - Update `EMAIL_ADDRESS` and `EMAIL_PASSWORD` in `config.py`
   - Or set environment variables: `EMAIL_ADDRESS` and `EMAIL_PASSWORD`

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

### API Configuration
```python
# config.py
API_KEY = 'your-financial-modeling-prep-api-key'
```

### Email Settings
```python
# config.py
EMAIL_ADDRESS = 'your-email@gmail.com'
EMAIL_PASSWORD = 'your-app-password'
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
```

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

See `requirements.txt` for complete list.

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
├── requirements.txt      # Python dependencies
├── email_settings.json   # Email configuration storage
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

