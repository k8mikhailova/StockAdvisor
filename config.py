import os
from datetime import time

# Replace with your API from Financial Modeling Prep API website
API_KEY = 'zhzleqfh71Kmb7zRXqR96MMPbZqSW6PN'

# Email settings
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "katemo03el@gmail.com")
EMAIL_PASSWORD = os.getenv("katemo03el@gmail.com", "qjzm eqyj cwmx hfdz")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# Default settings for the app
DEFAULT_CALCULATION_TIME = time(17, 0)
DEFAULT_EMAIL_TIME = time(19, 0)

# File paths
SETTINGS_FILE_PATH = "settings.txt"
