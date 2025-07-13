import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import os
import sys
# Add the parent directory (or the directory where Logger.py is located) to the system path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# This line is commented out as it's no longer needed with the new folder structure.
# Create milvusLogs folder if it doesn't exist
log_dir = "microservices/logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Get current timestamp for log file name
current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file = os.path.join(log_dir, f"{current_datetime}.log")

# Set up rotating log file handler (max 5MB per file, keeps 3 backups)
handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)

# Configure logging with timestamp for each log entry
logging.basicConfig(
    handlers=[handler],
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',  # Logs will contain the timestamp
    datefmt='%Y-%m-%d %H:%M:%S'  # Time format for each log entry
)

# Create logger instance
logger = logging.getLogger(__name__)

# Example log entry
logger.info("Logging setup complete. Log file saved in logs folder.")
