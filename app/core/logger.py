import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Configure logs directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Common Formatter
# File formatter includes more detail
FILE_FORMATTER = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s"
)
# Console formatter is cleaner for quick reading
CONSOLE_FORMATTER = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)

def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup as many loggers as you want"""
    
    # Create the logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # If logger already has handlers, don't add more (prevents duplicate logs)
    if logger.handlers:
        return logger

    # Rotating File Handler (prevents log files from growing infinitely)
    file_handler = RotatingFileHandler(
        LOG_DIR / log_file, 
        maxBytes=10*1024*1024, # 10MB
        backupCount=5
    )
    file_handler.setFormatter(FILE_FORMATTER)
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(CONSOLE_FORMATTER)
    logger.addHandler(console_handler)

    return logger

# Initialize specialized loggers
api_logger = setup_logger("api", "api.log")
error_logger = setup_logger("error", "error.log", level=logging.ERROR)
task_logger = setup_logger("tasks", "tasks.log")
default_logger = setup_logger("app", "app.log")
client_logger = setup_logger("client", "client.log")
