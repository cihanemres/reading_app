"""
Logging Configuration for Backend
Provides structured logging with rotation and different levels
"""
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
import os

# Create logs directory if not exists
LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Custom formatter for structured logs
class StructuredFormatter(logging.Formatter):
    def format(self, record):
        # Add timestamp
        record.timestamp = datetime.utcnow().isoformat()
        
        # Add extra context if available
        if not hasattr(record, 'user_id'):
            record.user_id = 'anonymous'
        if not hasattr(record, 'request_id'):
            record.request_id = '-'
            
        return super().format(record)

# Log format
LOG_FORMAT = '%(timestamp)s | %(levelname)-8s | %(name)s | user:%(user_id)s | %(message)s'
DETAILED_FORMAT = '%(timestamp)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | user:%(user_id)s | req:%(request_id)s | %(message)s'

def setup_logging(app_name: str = 'okuma-backend', level: str = 'INFO'):
    """
    Setup logging configuration
    
    Args:
        app_name: Application name for log files
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Console handler (for Render logs)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(StructuredFormatter(LOG_FORMAT))
    root_logger.addHandler(console_handler)
    
    # File handler with rotation (for local development)
    try:
        file_handler = RotatingFileHandler(
            os.path.join(LOGS_DIR, f'{app_name}.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(StructuredFormatter(DETAILED_FORMAT))
        root_logger.addHandler(file_handler)
        
        # Error file handler
        error_handler = RotatingFileHandler(
            os.path.join(LOGS_DIR, f'{app_name}-error.log'),
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter(DETAILED_FORMAT))
        root_logger.addHandler(error_handler)
    except Exception as e:
        # File logging might fail on Render - that's OK
        console_handler.setFormatter(StructuredFormatter(DETAILED_FORMAT))
        logging.warning(f"File logging disabled: {e}")
    
    # Reduce noise from third-party libraries
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    return root_logger

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module"""
    return logging.getLogger(name)

# Request logging middleware helper
class LogContext:
    """Context manager for adding request context to logs"""
    def __init__(self, user_id: str = None, request_id: str = None):
        self.user_id = user_id
        self.request_id = request_id
        self.old_factory = None
        
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        user_id = self.user_id
        request_id = self.request_id
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            record.user_id = user_id or 'anonymous'
            record.request_id = request_id or '-'
            return record
            
        logging.setLogRecordFactory(record_factory)
        return self
        
    def __exit__(self, *args):
        logging.setLogRecordFactory(self.old_factory)
