import functools
import logging
import traceback
import asyncio
from typing import Any, Optional, Type, Tuple, Callable

logger = logging.getLogger(__name__)


def try_catch(
    return_on_error: Any = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_level: str = "error",
    log_traceback: bool = True,
    reraise: bool = False,
    on_error_callback: Optional[Callable] = None
):
    """
    Enhanced decorator that catches exceptions with configurable behavior.

    Args:
        return_on_error: Value to return when an exception occurs (default: None)
        exceptions: Tuple of exception types to catch (default: (Exception,))
        log_level: Logging level for errors ("error", "warning", "info", "debug")
        log_traceback: Whether to include full traceback in logs (default: True)
        reraise: Whether to re-raise the exception after handling (default: False)
        on_error_callback: Optional callback function to execute on error,
                          receives (exception, func_name, args, kwargs)

    Examples:
        # Simple usage - returns None on error
        @try_catch()
        def risky_function():
            return 1 / 0

        # Return False on error for boolean operations
        @try_catch(return_on_error=False)
        def update_manifest(data):
            # ... update logic
            return True

        # Return empty dict for data fetching operations
        @try_catch(return_on_error={})
        def get_lesson_data():
            # ... fetch logic
            return data

        # Only catch specific exceptions
        @try_catch(exceptions=(ValueError, KeyError), return_on_error=[])
        def parse_data(input_str):
            # ... parsing logic
            return parsed_list

        # Log as warning instead of error
        @try_catch(log_level="warning", return_on_error=0)
        def calculate_progress():
            # ... calculation logic
            return percentage

        # Custom error callback
        def notify_error(exc, func_name, args, kwargs):
            send_notification(f"Function {func_name} failed: {exc}")

        @try_catch(on_error_callback=notify_error)
        def critical_operation():
            # ... critical logic
            pass
    """
    def decorator(func):
        # Check if function is async
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    # Prepare error message
                    error_msg = f"Error in {func.__name__}: {e}"
                    if log_traceback:
                        error_msg += f"\n{traceback.format_exc()}"

                    # Log at appropriate level
                    log_method = getattr(logger, log_level.lower(), logger.error)
                    log_method(error_msg)

                    # Execute callback if provided
                    if on_error_callback:
                        try:
                            on_error_callback(e, func.__name__, args, kwargs)
                        except Exception as callback_error:
                            logger.error(f"Error in callback for {func.__name__}: {callback_error}")

                    # Re-raise if requested
                    if reraise:
                        raise

                    # Return configured value
                    return return_on_error

            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    # Prepare error message
                    error_msg = f"Error in {func.__name__}: {e}"
                    if log_traceback:
                        error_msg += f"\n{traceback.format_exc()}"

                    # Log at appropriate level
                    log_method = getattr(logger, log_level.lower(), logger.error)
                    log_method(error_msg)

                    # Execute callback if provided
                    if on_error_callback:
                        try:
                            on_error_callback(e, func.__name__, args, kwargs)
                        except Exception as callback_error:
                            logger.error(f"Error in callback for {func.__name__}: {callback_error}")

                    # Re-raise if requested
                    if reraise:
                        raise

                    # Return configured value
                    return return_on_error

            return sync_wrapper

    # Support both @try_catch and @try_catch() syntax
    if callable(return_on_error) and not isinstance(return_on_error, type):
        # Called as @try_catch without parentheses
        func = return_on_error
        return_on_error = None
        return decorator(func)

    return decorator


# Convenience aliases for common use cases
def try_catch_bool(func):
    """Decorator that returns False on error - useful for update/write operations."""
    return try_catch(return_on_error=False)(func)


def try_catch_dict(func):
    """Decorator that returns empty dict on error - useful for data fetching."""
    return try_catch(return_on_error={})(func)


def try_catch_list(func):
    """Decorator that returns empty list on error - useful for listing operations."""
    return try_catch(return_on_error=[])(func)


def try_catch_none(func):
    """Decorator that returns None on error - the default behavior."""
    return try_catch(return_on_error=None)(func)