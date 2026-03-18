"""
Centralized logging configuration module for DataChat application.

This module provides standardized logging functionality including:
- JSON-formatted structured logging
- Request ID tracking and correlation
- Log rotation and retention policies
- Performance metric logging utilities
- Environment-specific log level configuration
"""
import json
import logging
import sys
import time
import uuid
from logging.handlers import RotatingFileHandler
from datetime import datetime
import os
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator, Callable

# Configure environment-based log levels
LOG_LEVELS = {
    "development": logging.DEBUG,
    "testing": logging.DEBUG,
    "staging": logging.INFO,
    "production": logging.WARNING
}

# Get environment or default to development
ENV = os.getenv("ENVIRONMENT", "development")
DEFAULT_LOG_LEVEL = LOG_LEVELS.get(ENV, logging.INFO)

# Context for tracking request information across the application
class RequestContext:
    """
    Thread-local storage for request context information.
    Maintains correlation IDs and other metadata across the application.
    """
    _request_id = None
    _user_id = None
    _session_id = None
    _additional_context = {}

    @classmethod
    def set_request_id(cls, request_id: Optional[str] = None) -> str:
        """
        Set the current request ID or generate a new one.
        
        Args:
            request_id: Optional existing request ID to use
            
        Returns:
            The request ID that was set
        """
        cls._request_id = request_id or str(uuid.uuid4())
        return cls._request_id

    @classmethod
    def get_request_id(cls) -> Optional[str]:
        """Get the current request ID."""
        return cls._request_id
    
    @classmethod
    def set_user_id(cls, user_id: str) -> None:
        """Set the current user ID."""
        cls._user_id = user_id
        
    @classmethod
    def get_user_id(cls) -> Optional[str]:
        """Get the current user ID."""
        return cls._user_id
    
    @classmethod
    def set_session_id(cls, session_id: str) -> None:
        """Set the current session ID."""
        cls._session_id = session_id
        
    @classmethod
    def get_session_id(cls) -> Optional[str]:
        """Get the current session ID."""
        return cls._session_id
    
    @classmethod
    def add_context(cls, key: str, value: Any) -> None:
        """Add a key-value pair to the context."""
        cls._additional_context[key] = value
        
    @classmethod
    def get_context(cls, key: str) -> Any:
        """Get a value from the context by key."""
        return cls._additional_context.get(key)
    
    @classmethod
    def get_all_context(cls) -> Dict[str, Any]:
        """Get all context data including IDs."""
        context = cls._additional_context.copy()
        if cls._request_id:
            context["request_id"] = cls._request_id
        if cls._user_id:
            context["user_id"] = cls._user_id
        if cls._session_id:
            context["session_id"] = cls._session_id
        return context
    
    @classmethod
    def clear(cls) -> None:
        """Clear all context data."""
        cls._request_id = None
        cls._user_id = None
        cls._session_id = None
        cls._additional_context = {}


# Custom JSON Formatter
class JsonFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as JSON objects.
    Includes timestamps, context information, and any additional properties.
    """
    def format(self, record):
        """
        Format the log record as a JSON object.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON string representation of the log record
        """
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add request context if available
        request_context = RequestContext.get_all_context()
        if request_context:
            log_record.update(request_context)
            
        # Add exception info if available
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        # Add extra fields from record
        if hasattr(record, 'props'):
            log_record.update(record.props)
            
        return json.dumps(log_record)


# Context manager for timing operations
@contextmanager
def log_execution_time(logger, operation_name: str) -> Generator[None, None, None]:
    """
    Context manager that logs the execution time of an operation.
    
    Args:
        logger: Logger instance to use
        operation_name: Name of the operation being timed
        
    Yields:
        None
        
    Example:
        ```
        logger = get_logger(__name__)
        with log_execution_time(logger, "database_query"):
            result = execute_query(...)
        ```
    """
    start_time = time.time()
    try:
        yield
    finally:
        execution_time = time.time() - start_time
        logger.info(
            f"Operation {operation_name} completed",
            extra={"props": {"operation": operation_name, "execution_time_ms": round(execution_time * 1000, 2)}}
        )


def get_logger(name: str, log_level: Optional[int] = None) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Name for the logger, typically __name__ of the calling module
        log_level: Optional override for log level
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # If logger already has handlers, return it to avoid duplicate handlers
    if logger.handlers:
        return logger
        
    # Set log level from param or default 
    logger.setLevel(log_level or DEFAULT_LOG_LEVEL)
    
    # Console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JsonFormatter())
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "datachat.log"),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)
    
    return logger


def log_with_props(logger, level: str, message: str, **props):
    """
    Log a message with additional properties that get included in the JSON output.
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        props: Additional properties to include in the log
    """
    log_method = getattr(logger, level.lower())
    log_method(message, extra={"props": props})


# Function decorator for logging function calls
def log_function_call(logger=None):
    """
    Decorator that logs function entry and exit with timing information.
    
    Args:
        logger: Logger instance to use (if None, will use the module's logger)
        
    Returns:
        Decorated function
        
    Example:
        ```
        @log_function_call(logger)
        def process_data(data):
            # function body
        ```
    """
    def decorator(func: Callable):
        # If logger not provided, get one based on the function's module
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
            
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(f"Entering function: {func_name}")
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.debug(
                    f"Exiting function: {func_name}",
                    extra={"props": {"function": func_name, "execution_time_ms": round(execution_time * 1000, 2)}}
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Exception in function: {func_name} - {str(e)}",
                    extra={"props": {"function": func_name, "execution_time_ms": round(execution_time * 1000, 2)}},
                    exc_info=True
                )
                raise
                
        return wrapper
    
    return decorator