import logging
from pathlib import Path


# Configure logs directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Console formatter is cleaner for quick reading
CONSOLE_FORMATTER = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def setup_logger(name, level=logging.INFO, extra=None):
    """Function to setup as many loggers as you want"""
    
    # Create the logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # If logger already has handlers, don't add more (prevents duplicate logs)
    if logger.handlers:
        return logger

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(CONSOLE_FORMATTER)
    logger.addHandler(console_handler)

    return logger

# Initialize specialized loggers
api_logger = setup_logger("api")
error_logger = setup_logger("error", level=logging.ERROR)
task_logger = setup_logger("tasks")
default_logger = setup_logger("app")
client_logger = setup_logger("client")
