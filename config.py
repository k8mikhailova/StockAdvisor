import os
from datetime import time


def _get_setting(name, default=None):
    """
    Read a setting from environment variables first, then from Streamlit secrets (.streamlit/secrets.toml or the
    Streamlit Community Cloud "Secrets" panel). Credentials must never be hardcoded in this file.
    """
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets.get(name, default)
    except Exception:
        # no secrets file, or streamlit is not available (e.g. when running to_email.py)
        return default


# Financial Modeling Prep API key (only needed in live mode)
API_KEY = _get_setting("FMP_API_KEY")

# email settings (only needed by the to_email.py automation script, never by the public demo)
EMAIL_ADDRESS = _get_setting("EMAIL_ADDRESS")
EMAIL_PASSWORD = _get_setting("EMAIL_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# demo mode uses the bundled historical data in data.csv, makes no API calls and never sends emails.
# it is the default; live mode must be enabled explicitly with STOCKADVISOR_MODE="live" and a configured API key.
LIVE_MODE = str(_get_setting("STOCKADVISOR_MODE", "demo")).lower() == "live" and bool(API_KEY)
DEMO_MODE = not LIVE_MODE

# default settings for the app
DEFAULT_CALCULATION_TIME = time(17, 0)
DEFAULT_EMAIL_TIME = time(19, 0)

# file paths
APP_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE_PATH = os.path.join(APP_DIR, "email_settings.json")
PARAMETERS_FILE_PATH = os.path.join(APP_DIR, "parameters.json")
HISTORICAL_DATA_PATH = os.path.join(APP_DIR, "data.csv")  # bundled sample data used by demo mode (read-only)
