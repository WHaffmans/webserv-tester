#!/usr/bin/env python3
"""
Logger Utility

Provides consistent logging throughout the test framework.
"""

import logging
import sys
import os
import re
from pathlib import Path
import time

# Global logger instance
_logger = None
_console_handler = None
_file_handler = None
_current_test = None
_failed_tests_log = None  # Track failed tests log file
_saved_source_file = None  # Track path to saved source file


# Timing threshold in seconds - only show timing if it exceeds this value
TIMING_THRESHOLD = 0.5

# Column alignment width for test names
TEST_NAME_WIDTH = 38
SEPARATOR_WIDTH = 56

# Terminal colors
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"

# Emoji indicators
class Emoji:
    SUCCESS = "✅"
    BIG_SUCCESS = "🎉"
    FAIL = "❌"
    SKIP = "⏩"
    INFO = "ℹ️"
    WARNING = "⚠️"
    ERROR = "🔥"
    RUNNING = "🔄"
    START = "🚀"
    END = "🏁"
    TIME = "⏱️"
    WEBSERV = "📡"
    LIST = "📋"
    DETAIL = "🔍"
    FILE = "🐍"

# Function to strip ANSI color codes
def strip_ansi_codes(text):
    """Remove ANSI escape sequences from text"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

# Get tester root directory (parent of core directory)
def get_tester_root():
    """Get the absolute path to the tester root directory."""
    # Find the core directory (where this file is)
    core_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    # The tester directory is the parent of core
    return core_dir.parent

# Custom formatter that strips ANSI codes and formats timestamps/levels
class FileFormatter(logging.Formatter):
    def format(self, record):
        # Save original formatTime method
        orig_format_time = self.formatTime
        
        # Override formatTime to use custom format
        def custom_format_time(record, datefmt=None):
            # Format with simpler timestamp (YYYY-MM-DD HH:MM)
            return time.strftime("%Y-%m-%d %H:%M", time.localtime(record.created))
            
        self.formatTime = custom_format_time
        
        # Generate the formatted record
        formatted = super().format(record)
        
        # Restore original formatTime
        self.formatTime = orig_format_time
        
        # Strip ANSI codes
        return strip_ansi_codes(formatted)
        
    def formatMessage(self, record):
        # Custom level formatting
        if record.levelno == logging.INFO:
            # For INFO level, remove the level indicator completely
            record.levelname = ""
            return f"{self.formatTime(record)} {record.message}"
        else:
            # For other levels, format as [LEVEL]
            return f"{self.formatTime(record)} [{record.levelname}] {record.message}"

def setup_logger(level=logging.INFO):
    """
    Set up the global logger.
    
    Args:
        level (int): Logging level
    """
    global _logger, _console_handler, _file_handler
    if _logger is not None:
        return _logger
    
    # Create logger
    _logger = logging.getLogger('webserv_tester')
    _logger.setLevel(logging.DEBUG)  # Always use DEBUG for the logger itself
    
    # Get tester root directory and create logs directory directly in tester
    tester_root = get_tester_root()
    logs_dir = tester_root / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Create console handler with custom formatter
    _console_handler = logging.StreamHandler(sys.stdout)
    _console_handler.setLevel(level)
    
    # Create file handler for detailed logging
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    log_file = logs_dir / f"tester-{timestamp}.log"
    _file_handler = logging.FileHandler(log_file, mode='w')
    _file_handler.setLevel(logging.DEBUG)  # Always log everything to file
    
    # Create formatters
    console_format = logging.Formatter('%(message)s')
    file_format = FileFormatter('%(message)s')  # We now handle formatting in the formatter class
    
    # Attach formatters
    _console_handler.setFormatter(console_format)
    _file_handler.setFormatter(file_format)
    
    # Add handlers to logger
    _logger.addHandler(_console_handler)
    _logger.addHandler(_file_handler)
    
    # Log the start of the testing session with separator lines
    logger = _logger  # For convenience
    logger.info("─" * SEPARATOR_WIDTH)
    logger.info(f"{Emoji.WEBSERV} {Colors.BOLD}WebServ Testing{Colors.RESET}")
    logger.info("─" * SEPARATOR_WIDTH)
    
    return _logger

def get_logger():
    """
    Get the global logger instance.
    
    Returns:
        logging.Logger: Logger instance
    """
    global _logger
    if _logger is None:
        _logger = setup_logger()
    
    return _logger

def log_test_start(category, test_name):
    """
    Log the start of a test.
    
    Args:
        category (str): Test category
        test_name (str): Test name
    """
    global _current_test
    logger = get_logger()
    
    # Store test name without category for log_test_result to use
    # Removed the colon after test name
    _current_test = f"{Emoji.RUNNING} {test_name}"

def log_test_result(category, test_name, passed, duration, error=None):
    """
    Log the result of a test.
    
    Args:
        category (str): Test category
        test_name (str): Test name
        passed (bool): Whether the test passed
        duration (float): Test duration in seconds
        error (str, optional): Error message if the test failed
    """
    global _current_test
    logger = get_logger()
    
    if passed:
        status_emoji = Emoji.SUCCESS
        status_text = f"{Colors.GREEN}PASS{Colors.RESET}"
    else:
        status_emoji = Emoji.FAIL
        status_text = f"{Colors.RED}FAIL{Colors.RESET}"
    
    # Include timing only if it exceeds threshold
    timing_info = f" {Emoji.TIME} {duration:.2f}s" if duration > TIMING_THRESHOLD else ""
    
    # Format complete test result on a single line with alignment
    if _current_test:
        # Pad the test name to align results column
        test_display = _current_test.ljust(TEST_NAME_WIDTH)
        message = f"{test_display} {status_emoji} {status_text}{timing_info}"
    else:
        # Fallback if _current_test is not set
        # Removed the colon after test name
        test_display = f"{Emoji.RUNNING} {test_name}".ljust(TEST_NAME_WIDTH)
        message = f"{test_display} {status_emoji} {status_text}{timing_info}"
    
    logger.info(message)
    _current_test = None

def log_category_header(category):
    """
    Log a category header.
    
    Args:
        category (str): Test category
    """
    # Remove the "Tests" suffix from the category name
    if category.endswith("Tests"):
        category = category[:-5]  # Remove the last 5 characters ("Tests")
    
    # Restore category header display in console
    logger = get_logger()
    logger.info("")
    logger.info(f"{Emoji.INFO}  {Colors.BOLD}{Colors.BLUE}{category}{Colors.RESET}")
    logger.info("─" * SEPARATOR_WIDTH)

def set_saved_source_file(path):
    """Set the path to the saved source file."""
    global _saved_source_file
    _saved_source_file = str(path)  # Convert Path to string

# Modify the log_summary function to include saved source file
def log_summary(passed, failed, total, duration, is_comprehensive=False):
    """
    Log a summary of test results.
    
    Args:
        passed (int): Number of passed tests
        failed (int): Number of failed tests
        total (int): Total number of tests
        duration (float): Total duration in seconds
        is_comprehensive (bool): Whether this was a comprehensive test run
    """
    global _file_handler, _failed_tests_log, _saved_source_file
    logger = get_logger()
    success_rate = (passed / total * 100) if total > 0 else 0
    
    logger.info("")
    logger.info("─" * SEPARATOR_WIDTH)
    
    # Show special message for comprehensive test runs with no failures
    if failed == 0 and is_comprehensive and total > 0:
        logger.info(f"{Emoji.BIG_SUCCESS} {Colors.BOLD}{Colors.GREEN}All tests passed!{Colors.RESET}")
        logger.info("─" * SEPARATOR_WIDTH)
    else:
        logger.info(f"{Emoji.END} {Colors.BOLD}Test Results Summary{Colors.RESET}")
        logger.info("─" * SEPARATOR_WIDTH)
    
    padding = " " * (len("Total duration:") - len("Total tests:"))
    logger.info(f"{Emoji.INFO}  Total tests:{padding} {Colors.BOLD}{total}{Colors.RESET}")
    padding = " " * (len("Total duration:") - len("Passed:"))
    logger.info(f"{Emoji.SUCCESS} Passed:{padding} {Colors.GREEN}{passed}{Colors.RESET}")
    padding = " " * (len("Total duration:") - len("Failed:"))
    if failed > 0:
        logger.info(f"{Emoji.FAIL} Failed:{padding} {Colors.RED}{failed}{Colors.RESET}")
    else:
        logger.info(f"{Emoji.SUCCESS} Failed:{padding} {Colors.GREEN}0{Colors.RESET}")
    logger.info(f"{Emoji.TIME}  Total duration: {Colors.CYAN}{duration:.2f}s{Colors.RESET}")
    logger.info("")
    
    # Always display the failed tests log line, whether there are failures or not
    if failed > 0:
        # Ensure _failed_tests_log is set before logging
        if _failed_tests_log is None:
            tester_root = get_tester_root()
            logs_dir = tester_root / 'logs'
            logs_dir.mkdir(exist_ok=True)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            _failed_tests_log = logs_dir / f"failed-tests-{timestamp}.log"
        logger.info(f"{Emoji.LIST} List of fails: {Colors.CYAN}{_failed_tests_log}{Colors.RESET}")
    else:
        logger.info(f"{Emoji.LIST} List of tests: None")
    
    logger.info(f"{Emoji.DETAIL} Detailed logs: {Colors.CYAN}{_file_handler.baseFilename}{Colors.RESET}")
    
    # Add information about saved source file if it exists
    if _saved_source_file:
        logger.info(f"{Emoji.FILE} Test source: {Colors.CYAN}{_saved_source_file}{Colors.RESET}")

def log_failed_tests(failed_tests):
    """
    Log details of failed tests to a dedicated log file instead of the console.
    
    Args:
        failed_tests (list): List of (test_name, error) tuples
    """
    global _failed_tests_log
    
    if not failed_tests:
        return
    
    logger = get_logger()
    
    # Create a dedicated log file for failed tests
    tester_root = get_tester_root()
    logs_dir = tester_root / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Use a timestamp-based filename
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    failed_log_file = logs_dir / f"failed-tests-{timestamp}.log"
    
    try:
        # Write failed tests to the dedicated log file
        with open(failed_log_file, 'w') as f:
            f.write("Failed Tests:\n")
            f.write("─" * SEPARATOR_WIDTH + "\n\n")
            
            for i, (test_name, error) in enumerate(failed_tests):
                f.write(f"{i+1}. {test_name}\n")
                f.write(f"   Error: {error}\n\n")
        
        # Store the log file path for use in log_summary
        _failed_tests_log = failed_log_file
        
    except Exception as e:
        # If we can't write to the failed tests log, log an error and continue
        logger.error(f"Error creating failed tests log: {e}")
        # Fall back to logging to the console/main log file
        logger.info("")
        logger.info(f"{Colors.RED}{Colors.BOLD}Failed Tests:{Colors.RESET}")
        logger.info("─" * SEPARATOR_WIDTH)
        
        for i, (test_name, error) in enumerate(failed_tests):
            logger.info(f"{i+1}. {Colors.RED}{test_name}{Colors.RESET}")
            logger.info(f"   Error: {error}")
            logger.info("")