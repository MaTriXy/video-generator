"""
Simplified process-isolated logging configuration for the course workflow system.
Each process gets a single log file containing all logging output.
"""

import logging
import sys
import os
from pathlib import Path
from datetime import datetime
import unicodedata

# Ensure logs directory exists
PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Environment-based log level
ENV = os.getenv('ENV', 'prod').lower()
DEFAULT_LOG_LEVEL = logging.DEBUG if ENV == 'dev' else logging.INFO

# Global console logging control (default: enabled)
_CONSOLE_LOGGING_ENABLED = True

class SafeStreamHandler(logging.StreamHandler):
    """Custom StreamHandler that safely handles Unicode characters and respects console logging control"""

    def emit(self, record):
        global _CONSOLE_LOGGING_ENABLED

        # Skip console output if console logging is disabled (except for ERROR and CRITICAL)
        if not _CONSOLE_LOGGING_ENABLED and record.levelno < logging.ERROR:
            return

        try:
            msg = self.format(record)
            # Replace any Unicode characters that can't be encoded
            # This will replace emojis and other problematic characters with their names or '?'
            try:
                # Try to encode with the current encoding
                encoding = getattr(self.stream, 'encoding', 'utf-8') or 'utf-8'
                if encoding.lower() in ['cp1252', 'charmap', 'ascii']:
                    # For limited encodings, replace problematic characters
                    safe_msg = ''.join(
                        char if ord(char) < 128 else f'[{unicodedata.name(char, "?").replace(" ", "_")}]'
                        if ord(char) > 127 and ord(char) < 256
                        else '[emoji]' if ord(char) > 0x1F300 and ord(char) < 0x1F9FF
                        else '?'
                        for char in msg
                    )
                    msg = safe_msg
            except Exception:
                # Fallback: remove all non-ASCII characters
                msg = msg.encode('ascii', 'replace').decode('ascii')

            self.stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

def get_workflow_name() -> str:
    """Extract workflow name from command line or script name"""
    if len(sys.argv) > 1:
        # For course_cli.py course-outline -> "course-outline"  
        if 'course_cli.py' in sys.argv[0]:
            return sys.argv[1]
        else:
            # For direct script execution -> script name
            return Path(sys.argv[0]).stem
    else:
        # Fallback to script name
        return Path(sys.argv[0]).stem

def get_process_log_file(log_file_name: str = None, log_file_dir: Path = None) -> Path:
    workflow = get_workflow_name()
    if log_file_name:
        filename = f"{log_file_name}.log"
    else:
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        pid = os.getpid()
        filename = f"{workflow}_{timestamp}_{pid}.log"

    if log_file_dir:
        log_dir = Path(log_file_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / filename

    return LOGS_DIR / filename

# Global process log file (set once per process)
_PROCESS_LOG_FILE = get_process_log_file()

def setup_logger(name: str, level: int = None, log_file_name: str = None, log_file_dir: Path = None) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.propagate = False
    logger.setLevel(level or DEFAULT_LOG_LEVEL)

    formatter = logging.Formatter(
        '%(asctime)s - [%(name)s] - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    global _PROCESS_LOG_FILE
    _PROCESS_LOG_FILE = get_process_log_file(log_file_name=log_file_name, log_file_dir=log_file_dir)
    file_path = _PROCESS_LOG_FILE
    file_handler = logging.FileHandler(file_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# Simplified convenience functions (all use same setup)
def get_agent_logger(agent_name: str) -> logging.Logger:
    """Get logger for agent scripts"""
    return setup_logger(f'agent.{agent_name}')

def get_orchestrator_logger() -> logging.Logger:
    """Get logger for orchestrator service"""
    return setup_logger('orchestrator')

def get_utility_logger(module_name: str, log_file_name: str = None, log_file_dir: Path = None) -> logging.Logger:
    return setup_logger(f'utils.{module_name}', log_file_name=log_file_name, log_file_dir=log_file_dir)

def get_streamlit_logger() -> logging.Logger:
    """Get logger for Streamlit app"""
    return setup_logger('streamlit_app')

def get_service_logger(service_name: str) -> logging.Logger:
    """Get logger for service components"""
    return setup_logger(f'service.{service_name}')

def get_controller_logger(controller_name: str) -> logging.Logger:
    """Get logger for controller components"""
    return setup_logger(f'controller.{controller_name}')

def get_deployment_logger(component_name: str = None) -> logging.Logger:
    """Get logger for deployment components"""
    name = f'deployment.{component_name}' if component_name else 'deployment'
    return setup_logger(name)

def get_test_logger() -> logging.Logger:
    """Get logger for test scripts"""
    return setup_logger('tests')

def setup_root_logger():
    """
    Set up the root logger with basic configuration.
    This should be called once at application startup.
    """
    root_logger = logging.getLogger()
    
    # Only configure if not already configured
    if not root_logger.handlers:
        # Use INFO level for dev, WARNING for prod
        root_level = logging.INFO if ENV == 'dev' else logging.WARNING
        root_logger.setLevel(root_level)
        
        # Console handler for root logger with safe Unicode handling
        console_handler = SafeStreamHandler(sys.stdout)
        console_handler.setLevel(root_level)
        
        formatter = logging.Formatter(
            '%(asctime)s - [%(name)s] - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Single file handler for root logger
        file_handler = logging.FileHandler(_PROCESS_LOG_FILE, encoding='utf-8')
        file_handler.setLevel(root_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

# Auto-configure root logger when module is imported
setup_root_logger()

# Utility function to get current process log file path
def get_current_log_file() -> Path:
    """Get the current process log file path"""
    return _PROCESS_LOG_FILE

def set_console_logging(enabled: bool = True):
    """
    Enable or disable console logging globally.

    Args:
        enabled: True to enable console logging, False to disable

    Note:
        - File logging is always enabled regardless of this setting
        - Default is True (console logging enabled)
    """
    global _CONSOLE_LOGGING_ENABLED
    _CONSOLE_LOGGING_ENABLED = enabled

def is_console_logging_enabled() -> bool:
    """Check if console logging is currently enabled"""
    global _CONSOLE_LOGGING_ENABLED
    return _CONSOLE_LOGGING_ENABLED