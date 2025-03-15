import logging
import sys

def setupLogging():
    # Create a formatter
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    
    # Create a console handler and set level to INFO
    console_handler = logging.StreamHandler(sys.stdout)  # Explicitly use stdout
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Create a file handler
    file_handler = logging.FileHandler("bot.log")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Get the root logger and clear existing handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Add a direct print for visibility
    print("LOGGING SETUP COMPLETE - THIS SHOULD BE VISIBLE IN RAILWAY LOGS")