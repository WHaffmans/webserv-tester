#!/usr/bin/env python3
"""
WebServ Tester - Main Entry Point

This script runs automated tests against the webserv HTTP server implementation.
It provides command-line options for running specific test suites or individual tests.
"""

import argparse
import sys
import time
import os
from pathlib import Path

# Add the tests directory to the Python path
tests_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

# Import our logger module first to ensure it's available
from core.logger import setup_logger, get_logger

# Then import initialization module
from core.initialization import initialize_environment

# Fixed test configuration path and main port - these are the only supported settings
TEST_CONFIG_PATH = "data/conf/test.conf"
DEFAULT_PORT = 8080

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test the webserv HTTP server implementation')
    
    parser.add_argument('--server-path', default='./webserv',
                        help='Path to the webserv executable')
    parser.add_argument('--host', default='127.0.0.1',
                        help='Host to connect to')
    parser.add_argument('--timeout', type=int, default=2,
                        help='Request timeout in seconds')
    parser.add_argument('--suite', 
                    choices=['basic', 'invalid', 'config', 'http', 'method', 
                            'upload', 'cgi', 'security', 
                            'performance', 'uri', 'cookie', 'redirect', 'all'],
                    default='all', help='Test suite to run')
    parser.add_argument('--test', help='Run a specific test by name')
    parser.add_argument('--startup-delay', type=float, default=1.0,
                        help='Delay in seconds after starting the server')
    
    return parser.parse_args()

def main():
    """Main entry point for the tester."""
    # Parse arguments first
    args = parse_arguments()
    
    # Setup logging with INFO level
    log_level = 20  # 20=INFO
    
    # Setup the enhanced logger FIRST
    setup_logger(log_level)
    logger = get_logger()
    
    # THEN initialize environment if needed
    initialize_environment()
    
    # Import remaining modules only after ensuring dependencies are installed
    from core.test_runner import TestRunner
    from core.server_manager import ServerManager
    from core.test_results import TestResults
    
    # Validate server path
    if not Path(args.server_path).exists():
        logger.error(f"Server executable not found at {args.server_path}")
        return 1
    
    # Validate fixed config path
    if not Path(TEST_CONFIG_PATH).exists():
        logger.error(f"Configuration file not found at {TEST_CONFIG_PATH}")
        return 1
    
    # Create test results collector
    results = TestResults()
    
    # Only start the server if we're not running the 'invalid' suite exclusively
    server = None
    if args.suite != 'invalid':
        # Start the server with the fixed test configuration
        server = ServerManager(args.server_path, TEST_CONFIG_PATH)
        if not server.start():
            logger.error("Failed to start the server")
            return 1

        # Wait for server to initialize
        logger.info(f"Waiting {args.startup_delay} seconds for server to start...")
        time.sleep(args.startup_delay)
    
    # Create test runner with connection parameters (using fixed default port)
    runner = TestRunner(args.host, DEFAULT_PORT, args.timeout, results)
    
    try:
        # Import test suites
        from tests_suites.basic_tests import BasicTests
        from tests_suites.config_tests import ConfigTests
        from tests_suites.invalid_config_tests import InvalidConfigTests
        from tests_suites.http_tests import HttpTests
        from tests_suites.method_tests import MethodTests
        from tests_suites.upload_tests import UploadTests
        from tests_suites.cgi_tests import CGITests
        from tests_suites.security_tests import SecurityTests
        from tests_suites.performance_tests import PerformanceTests
        from tests_suites.uri_tests import URITests
        from tests_suites.cookie_tests import CookieTests
        from tests_suites.redirect_tests import RedirectTests
        
        # Register test suites
        test_suites = {
            'basic': BasicTests(runner),
            'invalid': InvalidConfigTests(runner),
            'config': ConfigTests(runner),
            'http': HttpTests(runner),
            'method': MethodTests(runner),
            'uri': URITests(runner),
            'redirect': RedirectTests(runner),
            'upload': UploadTests(runner),
            'cgi': CGITests(runner),
            'cookie': CookieTests(runner),
            'security': SecurityTests(runner),
            'performance': PerformanceTests(runner),
        }
        
        # Run requested tests
        is_comprehensive = False
        if args.test:
            # Run a specific test if requested
            test_found = False
            for suite_name, suite in test_suites.items():
                if args.suite != 'all' and args.suite != suite_name:
                    continue
                
                for test_method in suite.get_test_methods():
                    if test_method.__name__ == args.test or test_method.__name__ == f"test_{args.test}":
                        suite.run_single_test(test_method.__name__)
                        test_found = True
                        break
                
                if test_found:
                    break
            
            if not test_found:
                logger.error(f"Test '{args.test}' not found")
                return 1
        else:
            # Run test suites
            if args.suite == 'all':
                is_comprehensive = True
                # Run basic tests first for smoke testing
                test_suites['basic'].run_all_tests()
                
                # Run the rest of the test suites
                for suite_name, suite in test_suites.items():
                    if suite_name != 'basic':  # Skip basic as we've already run it
                        suite.run_all_tests()
            else:
                # Run a specific test suite
                test_suites[args.suite].run_all_tests()
        
        # Stop the server if we started it (MOVED HERE: before results summary)
        if server is not None:
            server.stop()
            server = None  # Mark as already stopped
            
        # Print summary of results
        results.print_summary(is_comprehensive)
        
        # Return non-zero exit code if any tests failed
        passed, failed, _ = results.get_summary()
        return 1 if failed > 0 else 0
    
    finally:
        # Stop the server if we started it and it hasn't been stopped yet (failsafe)
        if server is not None:
            server.stop()

if __name__ == "__main__":
    sys.exit(main())