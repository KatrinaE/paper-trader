import logging
import os
from datetime import datetime

# Create logs directory if it doesn't exist
LOGS_DIR = 'logs'
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Get current date for log file name
DATE_STR = datetime.now().strftime('%Y-%m-%d')
LOG_FILE = os.path.join(LOGS_DIR, f'paper_trader_{DATE_STR}.log')

# Configure root logger with no handlers (we'll add them later)
logging.basicConfig(level=logging.INFO)

# Create handlers
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Get root logger and add handlers
root_logger = logging.getLogger()
root_logger.handlers = []  # Clear any existing handlers
root_logger.addHandler(file_handler)

# Set up module-specific loggers
logger = logging.getLogger('paper_trader')
logger.setLevel(logging.INFO)

# Configure logging levels for specific modules
logging.getLogger('market_data').setLevel(logging.INFO)
logging.getLogger('exchange').setLevel(logging.INFO)
logging.getLogger('rate_limiter').setLevel(logging.INFO)
logging.getLogger('trading_book').setLevel(logging.INFO)
logging.getLogger('user_actions').setLevel(logging.INFO)

# Log configuration
logger.info(f"Logging configured. Log file: {LOG_FILE}")
