#!/usr/bin/env python3
"""
Test Results

Collects and reports test results.
"""

import time
from core.logger import get_logger, log_summary, log_failed_tests, log_category_header

class TestResults:
    """Collects and reports test results."""
    
    def __init__(self):
        """Initialize the test results collector."""
        self.passed = []
        self.failed = []
        self.current_test = None
        self.current_test_start_time = None
        self.logger = get_logger()
        self.start_time = time.time()
        self.categories_seen = set()
    
    def start_test(self, test_name):
        """
        Mark the start of a test.
        
        Args:
            test_name (str): Name of the test
        """
        self.current_test = test_name
        self.current_test_start_time = time.time()
        
        # Check if this is a new category
        category = test_name.split('.')[0]
        if category not in self.categories_seen:
            self.categories_seen.add(category)
            log_category_header(category)
    
    def pass_test(self, test_name=None):
        """
        Mark a test as passed.
        
        Args:
            test_name (str, optional): Name of the test, defaults to current test
        """
        if test_name is None:
            test_name = self.current_test
        
        if test_name is None:
            self.logger.warning("No test name provided for pass_test")
            return
        
        duration = self._get_duration()
        self.passed.append((test_name, duration))
        
        self.current_test = None
        self.current_test_start_time = None
    
    def fail_test(self, error, test_name=None):
        """
        Mark a test as failed.
        
        Args:
            error (str): Error message or reason for failure
            test_name (str, optional): Name of the test, defaults to current test
        """
        if test_name is None:
            test_name = self.current_test
        
        if test_name is None:
            self.logger.warning("No test name provided for fail_test")
            return
        
        duration = self._get_duration()
        self.failed.append((test_name, error, duration))
        
        self.current_test = None
        self.current_test_start_time = None
    
    def _get_duration(self):
        """
        Calculate test duration.
        
        Returns:
            float: Test duration in seconds, or 0 if no start time
        """
        if self.current_test_start_time is None:
            return 0
        
        return time.time() - self.current_test_start_time
    
    def get_summary(self):
        """
        Get summary of test results.
        
        Returns:
            tuple: (passed_count, failed_count, total_count)
        """
        passed_count = len(self.passed)
        failed_count = len(self.failed)
        total_count = passed_count + failed_count
        
        return passed_count, failed_count, total_count
    
    def get_passed_tests(self):
        """
        Get list of passed tests.
        
        Returns:
            list: List of (test_name, duration) tuples
        """
        return self.passed
    
    def get_failed_tests(self):
        """
        Get list of failed tests.
        
        Returns:
            list: List of (test_name, error) tuples
        """
        return [(name, error) for name, error, _ in self.failed]
    
    def get_detailed_results(self):
        """
        Get detailed test results.
        
        Returns:
            dict: Dictionary with detailed test results
        """
        passed_count, failed_count, total_count = self.get_summary()
        
        return {
            'summary': {
                'total': total_count,
                'passed': passed_count,
                'failed': failed_count,
                'success_rate': (passed_count / total_count * 100) if total_count > 0 else 0
            },
            'passed': self.passed,
            'failed': self.failed
        }
    
    def print_summary(self, is_comprehensive=False):
        """
        Print summary of test results to console.
        
        Args:
            is_comprehensive (bool): Whether this was a comprehensive test run
        """
        passed_count, failed_count, total_count = self.get_summary()
        total_duration = time.time() - self.start_time
        
        log_summary(passed_count, failed_count, total_count, total_duration, is_comprehensive)
        
        if failed_count > 0:
            log_failed_tests(self.get_failed_tests())