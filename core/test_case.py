#!/usr/bin/env python3
"""
Test Case Base Class

Provides a foundation for implementing test cases.
"""

# Modify the imports at the top to include the new function
import inspect
import traceback
import time
from pathlib import Path
from core.logger import get_logger, log_test_start, log_test_result, set_saved_source_file

class TestCase:
    """Base class for test cases."""
    
    def __init__(self, runner):
        """
        Initialize the test case.
        
        Args:
            runner (TestRunner): Test runner instance
        """
        self.runner = runner
        self.logger = get_logger()
        self.current_test_name = None
        self.category_name = self.__class__.__name__.replace("Tests", "")
    
    def setup(self):
        """
        Set up the test environment.
        Called before each test.
        """
        pass
    
    def teardown(self):
        """
        Clean up the test environment.
        Called after each test, regardless of outcome.
        """
        pass
    
    def get_test_methods(self):
        """
        Get all test methods in this test case.
        
        Returns:
            list: List of test methods in source code order
        """
        # Get all test methods (those starting with 'test_')
        methods = [method for name, method in inspect.getmembers(self, predicate=inspect.ismethod)
                  if name.startswith('test_')]
        
        # Sort by line number in source code to maintain definition order
        methods.sort(key=lambda method: inspect.getsourcelines(method)[1])
        
        return methods
    
    def run_all_tests(self):
        """Run all test methods in this test case."""
        test_methods = self.get_test_methods()
        
        # No sorting needed here anymore, as get_test_methods already returns methods in source order
        
        for method in test_methods:
            self.run_test(method, save_source_on_failure=False)
    
    def run_single_test(self, test_name):
        """
        Run a single test by name.
        
        Args:
            test_name (str): Name of test method to run
            
        Returns:
            bool: True if test was found and executed, False otherwise
        """
        if not test_name.startswith('test_'):
            test_name = f'test_{test_name}'
        
        try:
            method = getattr(self, test_name)
            # Run the test with the flag to save the source code if it fails
            self.run_test(method, save_source_on_failure=True)
            return True
        except AttributeError:
            self.logger.error(f"Test '{test_name}' not found in {self.__class__.__name__}")
            return False
    
    def run_test(self, test_method, save_source_on_failure=False):
        """
        Run a single test method.
        
        Args:
            test_method (callable): Test method to run
            save_source_on_failure (bool): Whether to save the source code on failure
        """
        test_name = test_method.__name__
        self.current_test_name = test_name
        
        # Prepare descriptive test name by converting test_this_method to "This Method"
        descriptive_name = " ".join(word.capitalize() for word in test_name[5:].split('_'))
        
        # Log test start
        log_test_start(self.category_name, descriptive_name)
        
        # Track timing
        start_time = time.time()
        
        try:
            # Register with test results
            self.runner.results.start_test(f"{self.__class__.__name__}.{test_name}")
            
            # Run the test
            self.setup()
            test_method()
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Mark as passed
            self.runner.results.pass_test()
            log_test_result(self.category_name, descriptive_name, True, duration)
            
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            
            # Get error information
            error_trace = traceback.format_exc()
            error_msg = str(e)
            
            # Log the error (only to file, not console)
            self.logger.debug(f"Exception in {test_name}: {error_msg}")
            self.logger.debug(error_trace)
            
            # Mark as failed
            self.runner.results.fail_test(error_msg)
            log_test_result(self.category_name, descriptive_name, False, duration, error_msg)
            
            # Save the test function source code to a file if requested
            if save_source_on_failure:
                self._save_test_source(test_method, error_msg)
            
        finally:
            try:
                self.teardown()
            except Exception as e:
                self.logger.error(f"Exception in teardown for {test_name}: {e}")
            
            self.current_test_name = None

    # Then modify the _save_test_source method to use this function
    def _save_test_source(self, test_method, error_msg):
        """
        Save the source code of a failing test to a file in the logs directory.
        
        Args:
            test_method (callable): The failed test method
            error_msg (str): Error message from the exception
        """
        try:
            source_code = inspect.getsource(test_method)
            
            # Get the absolute path to the logs directory
            from core.path_utils import get_tester_root
            tester_root = get_tester_root()
            logs_dir = tester_root / 'logs'
            logs_dir.mkdir(exist_ok=True)
            
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            test_name = test_method.__name__
            class_name = self.__class__.__name__
            file_path = logs_dir / f"failed_test_{class_name}_{test_name}_{timestamp}.py"
            
            # Ensure we have an absolute path
            file_path = file_path.resolve()
            
            with open(file_path, "w") as f:
                f.write(f"# Failed test: {class_name}.{test_name}\n")
                f.write(f"# Error: {error_msg}\n\n")
                f.write(source_code)
            
            # Instead of immediate logging, store the path for summary
            set_saved_source_file(file_path)
        except Exception as save_error:
            self.logger.debug(f"Failed to save test source: {save_error}")
                            
    def assert_true(self, condition, message="Assertion failed"):
        """
        Assert that a condition is true.
        
        Args:
            condition: Condition to test
            message (str): Error message on failure
            
        Raises:
            AssertionError: If condition is not true
        """
        if not condition:
            raise AssertionError(message)
    
    def assert_false(self, condition, message="Assertion failed"):
        """
        Assert that a condition is false.
        
        Args:
            condition: Condition to test
            message (str): Error message on failure
            
        Raises:
            AssertionError: If condition is true
        """
        if condition:
            raise AssertionError(message)
    
    def assert_equals(self, actual, expected, message="Values not equal"):
        """
        Assert that two values are equal.
        
        Args:
            actual: Actual value
            expected: Expected value
            message (str): Error message on failure
            
        Raises:
            AssertionError: If values are not equal
        """
        if actual != expected:
            raise AssertionError(f"{message}: expected {expected}, got {actual}")
    
    def assert_not_equals(self, actual, expected, message="Values are equal"):
        """
        Assert that two values are not equal.
        
        Args:
            actual: Actual value
            expected: Expected value
            message (str): Error message on failure
            
        Raises:
            AssertionError: If values are equal
        """
        if actual == expected:
            raise AssertionError(f"{message}: both values are {actual}")
    
    def assert_contains(self, container, item, message="Item not found in container"):
        """
        Assert that container contains item.
        
        Args:
            container: Container to test
            item: Item to look for
            message (str): Error message on failure
            
        Raises:
            AssertionError: If item is not in container
        """
        if item not in container:
            raise AssertionError(f"{message}: {item} not found in {container}")
    
    def assert_not_contains(self, container, item, message="Unwanted item found in container"):
        """
        Assert that container does not contain item.
        
        Args:
            container: Container to test
            item: Item to look for
            message (str): Error message on failure
            
        Raises:
            AssertionError: If item is in container
        """
        if item in container:
            raise AssertionError(f"{message}: {item} found in {container}")