import os
from datetime import time

# replace with your API from Financial Modeling Prep API website
API_KEY = 'zhzleqfh71Kmb7zRXqR96MMPbZqSW6PN'

# email settings
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "katemo03el@gmail.com")
EMAIL_PASSWORD = os.getenv("katemo03el@gmail.com", "qjzm eqyj cwmx hfdz")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# default settings for the app
DEFAULT_CALCULATION_TIME = time(17, 0)
DEFAULT_EMAIL_TIME = time(19, 0)

# file paths
SETTINGS_FILE_PATH = "settings.txt"

# authentification settings
APP_PASSWORD = os.getenv("APP_PASSWORD", "12345")

