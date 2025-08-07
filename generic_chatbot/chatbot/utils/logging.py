"""
Logging utilities for the chatbot application.
Provides consistent logging patterns and helper functions.
"""

import functools
import logging
import time
from typing import Callable


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given module name.
    
    Args:
        name: The module name (usually __name__)
        
    Returns:
        A configured logger instance
    """
    return logging.getLogger(name)


def log_function_call(logger: logging.Logger, level: int = logging.DEBUG):
    """
    Decorator to log function calls with parameters and execution time.
    
    Args:
        logger: The logger instance to use
        level: The logging level for the function call log
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Log function entry
            logger.log(level, f"Entering {func.__name__} with args={args}, kwargs={kwargs}")
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.log(level, f"Exiting {func.__name__} successfully in {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Exiting {func.__name__} with exception after {execution_time:.3f}s: {e}")
                raise
        return wrapper
    return decorator


def log_async_function_call(logger: logging.Logger, level: int = logging.DEBUG):
    """
    Decorator to log async function calls with parameters and execution time.
    
    Args:
        logger: The logger instance to use
        level: The logging level for the function call log
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Log function entry
            logger.log(level, f"Entering async {func.__name__} with args={args}, kwargs={kwargs}")
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.log(level, f"Exiting async {func.__name__} successfully in {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Exiting async {func.__name__} with exception after {execution_time:.3f}s: {e}")
                raise
        return wrapper
    return decorator


def log_api_request(logger: logging.Logger, request_type: str = "API"):
    """
    Decorator to log API request/response details.
    
    Args:
        logger: The logger instance to use
        request_type: Type of request (API, WebSocket, etc.)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request info if available
            request_info = "Unknown"
            if args and hasattr(args[0], "method") and hasattr(args[0], "path"):
                request = args[0]
                request_info = f"{request.method} {request.path}"
            
            logger.info(f"Starting {request_type} request: {request_info}")
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"Completed {request_type} request: {request_info} in {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Failed {request_type} request: {request_info} after {execution_time:.3f}s: {e}")
                raise
        return wrapper
    return decorator


def log_database_operation(logger: logging.Logger, operation: str):
    """
    Decorator to log database operations.
    
    Args:
        logger: The logger instance to use
        operation: Description of the database operation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.debug(f"Starting database operation: {operation}")
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.debug(f"Completed database operation: {operation} in {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Failed database operation: {operation} after {execution_time:.3f}s: {e}")
                raise
        return wrapper
    return decorator


def log_external_service_call(logger: logging.Logger, service_name: str):
    """
    Decorator to log external service calls (API, S3, etc.).
    
    Args:
        logger: The logger instance to use
        service_name: Name of the external service
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.debug(f"Calling external service: {service_name}")
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.debug(f"External service call successful: {service_name} in {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"External service call failed: {service_name} after {execution_time:.3f}s: {e}")
                raise
        return wrapper
    return decorator
