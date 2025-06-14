#!/bin/bash
# Webserv test runner with easy-to-configure options

# -----------------------------------------
# Set these variables to configure your tests

# Test suite to run :
# all, basic, config, invalid, 
# http, method, upload, uri, redirect,
# cgi, cookie,
# security, performance
SUITE="all"

# Set to empty string to run full suite, or specify a test name
# Example: SINGLE_TEST="test_server_running"
SINGLE_TEST=""

# Time to wait after starting the server (seconds)
STARTUP_DELAY=0.1

# Clean log files before running tests (true/false)
CLEAN_LOGS="true"

# -----------------------------------------
# You can set these variables too, but they are guaranteed to work

# Path to webserv executable
SERVER_PATH="../webserv"

# Server ports are fixed in test.conf (8080, 8081, 8082)

# -----------------------------------------

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

BUILD_TARGET="all"

# Run make before executing tests
echo "Building webserv (target: $BUILD_TARGET)..."
cd "$PROJECT_ROOT"
make $BUILD_TARGET
MAKE_STATUS=$?

if [ $MAKE_STATUS -ne 0 ]; then
    echo "Error: Build failed. Fix compilation errors before running tests."
    exit 1
fi

# Return to the tests directory
cd "$SCRIPT_DIR"

# Clean log files if enabled
if [ "$CLEAN_LOGS" = "true" ]; then
    LOGS_DIR="logs"
    if [ -d "$LOGS_DIR" ]; then
        echo -n "Cleaning log files: "
        COUNT=$(find "$LOGS_DIR" -type f | wc -l | tr -d ' ')
        rm -f "$LOGS_DIR"/*
        echo "$COUNT log files removed."
    else
        echo "Logs directory not found, skipping cleanup."
    fi
fi

# Find Python command
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found. Please install Python 3."
    exit 1
fi

# Main script path
MAIN_SCRIPT="bin/run_tests.py"

# If SUITE empty, run all tests
if [ -z "$SUITE" ]; then
    SUITE="all"
fi

# Build command
CMD="$PYTHON_CMD $MAIN_SCRIPT --suite $SUITE --server-path $SERVER_PATH --startup-delay $STARTUP_DELAY"

# Add specific test if set
if [ ! -z "$SINGLE_TEST" ]; then
  CMD="$CMD --test $SINGLE_TEST"
fi

# Print the command
echo -n "Tester launched with command: "
echo "$CMD"

# Set PYTHONPATH to include the tests directory
export PYTHONPATH="$PYTHONPATH:."

# Run the command
$CMD