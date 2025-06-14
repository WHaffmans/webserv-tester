#!/usr/bin/env python3
"""
Performance and Stress Tests

Tests for server performance under load according to test.conf configuration.
Verifies handling of concurrent connections, resource utilization, and stability.
"""

import requests
import time
import random
import threading
import psutil
import os
import statistics
from concurrent.futures import ThreadPoolExecutor
from core.test_case import TestCase

class PerformanceTests(TestCase):
    """Tests server performance under various load conditions."""
    
    def setup(self):
        """Set up performance test environment."""
        # Define the test path that returns predictable content
        self.test_path = '/index.html'
        
        # Performance test parameters - using more demanding values for better performance validation
        self.num_concurrent = 500     # Number of concurrent connections in concurrency tests
        self.num_requests = 1000      # Total number of requests for load tests
        self.burst_size = 20         # Number of connections in a burst
        self.request_timeout = 0.1     # Timeout for requests in seconds
        
        # Get server process for resource monitoring
        try:
            self.server_pid = self._find_server_process()
            if self.server_pid:
                self.logger.debug(f"Found server process with PID: {self.server_pid}")
            else:
                self.logger.debug("Couldn't identify server process, some tests requiring resource monitoring may fail")
        except Exception as e:
            self.logger.debug(f"Error finding server process: {e}")
            self.server_pid = None
    
    def _find_server_process(self):
        """Find the server process ID based on common server executable names."""
        # Look for common server executable names
        server_names = ["webserv", "httpd", "nginx"]
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Check for known server names
                # Check in process name if available
                proc_name = proc.info.get('name', '')
                if proc_name and isinstance(proc_name, str):
                    proc_name = proc_name.lower()
                    for server_name in server_names:
                        if server_name in proc_name:
                            return proc.info['pid']
                
                # Check in command line arguments if available
                cmdline = proc.info.get('cmdline', [])
                if cmdline and isinstance(cmdline, (list, tuple)):
                    cmdline_str = ' '.join(cmdline).lower()
                    for server_name in server_names:
                        if server_name in cmdline_str:
                            return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, TypeError, AttributeError):
                continue
        
        # Default to None if we can't find the server process
        return None
    
    def _get_memory_usage(self):
        """Get memory usage of the server process."""
        if self.server_pid:
            try:
                # Get process and all children
                process = psutil.Process(self.server_pid)
                
                # Sum up memory usage from main process and all children
                memory_info = process.memory_info()
                memory_usage = memory_info.rss  # Resident Set Size in bytes
                
                # Add children's memory usage
                try:
                    for child in process.children(recursive=True):
                        try:
                            child_memory = child.memory_info().rss
                            memory_usage += child_memory
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                    # Some systems might not support children() method
                    pass
                
                return memory_usage
            except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                return None
        
        return None
    
    def _get_cpu_usage(self):
        """Get CPU usage percentage of the server process."""
        if self.server_pid:
            try:
                # Get process and all children
                process = psutil.Process(self.server_pid)
                
                # Get CPU percentage
                try:
                    cpu_percent = process.cpu_percent(interval=0.1)
                except (AttributeError, TypeError):
                    return None
                
                # Add children's CPU usage
                try:
                    for child in process.children(recursive=True):
                        try:
                            child_cpu = child.cpu_percent(interval=0.1)
                            cpu_percent += child_cpu
                        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                            continue
                except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                    # Some systems might not support children() method
                    pass
                
                return cpu_percent
            except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                return None
        
        return None
    
    def _send_request(self, index=0):
        """
        Send a single request to the server.
        
        Args:
            index (int): Request index for generating unique parameters
            
        Returns:
            tuple: (status_code, response_time, response_size, error_message)
        """
        # Add a unique query parameter to prevent caching
        url = f"{self.test_path}?req={index}&random={random.randint(1000, 9999)}"
        
        start_time = time.time()
        error_msg = None
        status_code = 0
        response_size = 0
        
        try:
            response = self.runner.send_request('GET', url, timeout=self.request_timeout)
            status_code = response.status_code
            response_size = len(response.content)
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
        
        response_time = time.time() - start_time
        return (status_code, response_time, response_size, error_msg)
    
    def test_concurrent_connections(self):
        """
        Test server handling of multiple concurrent connections.
        
        Verifies that the server can handle multiple simultaneous connections
        without errors, excessive delays, or connection failures.
        """
        try:
            # Use a ThreadPoolExecutor to manage concurrent requests
            with ThreadPoolExecutor(max_workers=self.num_concurrent) as executor:
                # Submit concurrent requests
                futures = [executor.submit(self._send_request, i) for i in range(self.num_concurrent)]
                
                # Collect results
                results = [future.result() for future in futures]
            
            # Analyze results
            successful = [r for r in results if r[0] == 200]
            failure_count = len(results) - len(successful)
            
            # There must be at least 85% successful requests to pass
            success_rate = len(successful) / len(results) if results else 0
            
            # Check minimum success threshold
            self.assert_true(success_rate >= 0.85, 
                          f"Too many concurrent request failures: success rate {success_rate*100:.1f}% (minimum required: 85%)")
            
            # Only calculate statistics if we have enough successful responses
            if len(successful) >= self.num_concurrent / 2:
                response_times = [r[1] for r in successful]
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
                
                # Log performance data
                self.logger.debug(f"Concurrent connections: {self.num_concurrent}")
                self.logger.debug(f"Successful responses: {len(successful)}/{len(results)}")
                self.logger.debug(f"Average response time: {avg_response_time:.4f} seconds")
                self.logger.debug(f"Maximum response time: {max_response_time:.4f} seconds")
                
                # Assert that response times are reasonable - expect sub-second performance
                self.assert_true(avg_response_time < 0.5, 
                              f"Average response time too high: {avg_response_time:.4f} seconds (maximum allowed: 0.5s)")
                
                # Maximum response time should not exceed 1 second
                self.assert_true(max_response_time < 1.0,
                              f"Maximum response time too high: {max_response_time:.4f} seconds (maximum allowed: 1.0s)")
            else:
                # Not enough successful responses for meaningful analysis
                self.assert_true(False, f"Not enough successful concurrent requests for performance analysis: {len(successful)}/{self.num_concurrent}")
                
        except Exception as e:
            self.logger.debug(f"Error during concurrent connections test: {e}")
            self.assert_true(False, f"Concurrent connections test failed: {e}")
    
    def test_rapid_requests(self):
        """
        Test server handling of rapid successive requests.
        
        Verifies that the server can handle many requests in quick succession
        without degrading performance or experiencing errors.
        """
        try:
            # Send many sequential requests as fast as possible
            results = []
            start_time = time.time()
            
            for i in range(self.num_requests):
                results.append(self._send_request(i))
            
            total_time = time.time() - start_time
            
            # Analyze results
            successful = [r for r in results if r[0] == 200]
            failure_count = len(results) - len(successful)
            
            # We need at least 30% successful requests for this test to be meaningful
            min_required = max(3, int(self.num_requests * 0.3))
            
            if len(successful) < min_required:
                self.assert_true(False, f"Too few successful rapid requests: {len(successful)}/{self.num_requests} (minimum {min_required} required)")
                return
                
            # Calculate response time statistics
            response_times = [r[1] for r in successful]
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            requests_per_second = len(results) / total_time if total_time > 0 else 0
            
            # Log performance data
            self.logger.debug(f"Total requests: {len(results)}")
            self.logger.debug(f"Total time: {total_time:.2f} seconds")
            self.logger.debug(f"Requests per second: {requests_per_second:.2f}")
            self.logger.debug(f"Successful responses: {len(successful)}/{len(results)}")
            self.logger.debug(f"Average response time: {avg_response_time:.4f} seconds")
            self.logger.debug(f"Maximum response time: {max_response_time:.4f} seconds")
            
            # Assert minimum performance - expect at least 50 requests per second
            self.assert_true(requests_per_second >= 50.0, 
                         f"Request throughput too low: {requests_per_second:.2f} req/s (minimum required: 50 req/s)")
            
            # Assert that most requests were successful (at least 85%)
            success_rate = len(successful) / len(results)
            self.assert_true(success_rate >= 0.85, 
                         f"Too many rapid request failures: success rate {success_rate*100:.1f}% (minimum required: 85%)")
                          
        except Exception as e:
            self.logger.debug(f"Error during rapid requests test: {e}")
            self.assert_true(False, f"Rapid requests test failed: {e}")
    
    def test_memory_usage_under_load(self):
        """
        Test server memory usage under load conditions.
        
        Verifies that the server does not have memory leaks or excessive
        memory consumption during sustained operation with multiple requests.
        """
        if not self.server_pid:
            self.logger.debug("Cannot identify server process - memory monitoring is required for this test")
            self.assert_true(False, "Memory monitoring is required for this test but server process could not be identified")
            return
        
        # Capture baseline memory
        baseline_memory = self._get_memory_usage()
        
        if baseline_memory is None:
            self.logger.debug("Cannot get baseline memory - memory monitoring is required for this test")
            self.assert_true(False, "Memory monitoring is required for this test but couldn't get baseline memory usage")
            return
        
        # Convert to MB for easier reading
        baseline_memory_mb = baseline_memory / (1024 * 1024)
        self.logger.debug(f"Baseline memory usage: {baseline_memory_mb:.2f} MB")
        
        # Run several batches of requests to induce potential memory issues
        test_batches = 3
        requests_per_batch = 30
        memory_samples = [baseline_memory]
        
        for batch in range(test_batches):
            self.logger.debug(f"Running request batch {batch+1}/{test_batches}")
            
            # Send concurrent requests in this batch
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(self._send_request, i) 
                          for i in range(requests_per_batch)]
                
                # Wait for all requests to complete
                results = [future.result() for future in futures]
                
                # Check if requests were successful
                successful = [r for r in results if r[0] == 200]
                success_rate = len(successful) / len(results) if results else 0
                self.logger.debug(f"Batch {batch+1} success rate: {success_rate*100:.1f}%")
                
                # If no successful requests, fail the test
                if not successful:
                    self.assert_true(False, f"No successful requests in batch {batch+1} - cannot continue memory test")
                    return
            
            # Capture memory after batch
            current_memory = self._get_memory_usage()
            if current_memory is None:
                self.assert_true(False, f"Lost ability to monitor memory during test - cannot continue memory test")
                return
                
            memory_samples.append(current_memory)
            current_memory_mb = current_memory / (1024 * 1024)
            self.logger.debug(f"Memory after batch {batch+1}: {current_memory_mb:.2f} MB")
        
        # Check for excessive memory growth - we need at least 3 samples for a meaningful test
        if len(memory_samples) < 3:
            self.assert_true(False, f"Insufficient memory samples ({len(memory_samples)}) for analysis")
            return
            
        max_memory = max(memory_samples)
        max_memory_mb = max_memory / (1024 * 1024)
        memory_growth = max_memory - baseline_memory
        growth_percent = (memory_growth / baseline_memory) * 100 if baseline_memory > 0 else 0
        
        self.logger.debug(f"Maximum memory usage: {max_memory_mb:.2f} MB")
        self.logger.debug(f"Memory growth: {memory_growth/(1024*1024):.2f} MB ({growth_percent:.1f}%)")
        
        # Check for memory growth trend (is it still growing after the last batch?)
        final_growth = memory_samples[-1] - memory_samples[-2]
        final_growth_mb = final_growth / (1024 * 1024)
        final_growth_percent = (final_growth / memory_samples[-2]) * 100 if memory_samples[-2] > 0 else 0
        
        self.logger.debug(f"Final batch growth: {final_growth_mb:.2f} MB ({final_growth_percent:.1f}%)")
        
        # We allow some memory growth, but it should stabilize
        # For this test, we'll check that either:
        # 1. Total growth is less than 50% (normal server memory utilization)
        # 2. Final batch growth is small (showing the trend is stabilizing)
        stable_memory = growth_percent < 50 or final_growth_percent < 10
        
        self.assert_true(stable_memory, 
                      f"Possible memory leak detected: growth {growth_percent:.1f}%, final batch growth {final_growth_percent:.1f}%")
    
    def test_connection_burst_handling(self):
        """
        Test server handling of sudden bursts of connections.
        
        Verifies that the server can handle rapid bursts of connections
        without failures or excessive delays.
        """
        # Run several bursts of connections with pauses between
        bursts = 3
        results_by_burst = []
        
        try:
            for burst in range(bursts):
                self.logger.debug(f"Sending connection burst {burst+1}/{bursts}")
                
                # Send a burst of concurrent connections
                with ThreadPoolExecutor(max_workers=self.burst_size) as executor:
                    # Submit concurrent requests for this burst
                    futures = [executor.submit(self._send_request, i + (burst * self.burst_size)) 
                              for i in range(self.burst_size)]
                    
                    # Collect results for this burst
                    burst_results = [future.result() for future in futures]
                    results_by_burst.append(burst_results)
                
                # Brief pause between bursts to let the server recover
                time.sleep(1)
        
            # Analyze results - all bursts must have some level of success
            successful_by_burst = []
            avg_response_times = []
            min_success_count = max(1, int(self.burst_size * 0.3))  # At least 30% should succeed
            
            for i, burst_results in enumerate(results_by_burst):
                successful = [r for r in burst_results if r[0] == 200]
                successful_by_burst.append(len(successful))
                
                # Each burst must have at least some successful requests
                if len(successful) < min_success_count:
                    self.assert_true(False, 
                                  f"Burst {i+1} had too few successful requests: {len(successful)}/{self.burst_size}")
                    return
                
                # Calculate average response time for successful requests
                response_times = [r[1] for r in successful]
                if response_times:
                    avg_time = statistics.mean(response_times)
                    avg_response_times.append(avg_time)
                else:
                    # We shouldn't reach here due to the check above, but just in case
                    avg_response_times.append(0)
            
            # Log performance data
            for i, (success_count, avg_time) in enumerate(zip(successful_by_burst, avg_response_times)):
                success_rate = success_count / self.burst_size
                self.logger.debug(f"Burst {i+1}: Success rate {success_rate*100:.1f}%, "
                                f"Avg response time {avg_time:.4f}s")
            
            # Only proceed with analysis if we have results from all bursts
            if len(successful_by_burst) < bursts:
                self.assert_true(False, f"Not all bursts completed: {len(successful_by_burst)}/{bursts}")
                return
            
            # Calculate minimum success rate across all bursts
            min_success_rate = min(s / self.burst_size for s in successful_by_burst)
            
            # Check if response times degraded significantly across bursts
            # (We're only interested in significant degradation that might indicate problems)
            if avg_response_times[0] > 0 and avg_response_times[-1] > 0:
                final_ratio = avg_response_times[-1] / avg_response_times[0]
                self.logger.debug(f"Response time ratio (last/first): {final_ratio:.2f}x")
                
                # Final burst shouldn't be more than 3x slower than first burst
                self.assert_true(final_ratio < 3, 
                              f"Performance severely degraded across bursts: {final_ratio:.2f}x slower")
            
            # Overall success assertion - must maintain reasonable success rates
            self.assert_true(min_success_rate >= 0.3, 
                          f"Connection burst handling inadequate: min success rate {min_success_rate*100:.1f}%")
            
        except Exception as e:
            self.logger.debug(f"Error during connection burst test: {e}")
            self.assert_true(False, f"Connection burst test failed: {e}")
    
    def test_response_time_consistency(self):
        """
        Test consistency of server response times.
        
        Verifies that the server maintains consistent response times
        across multiple similar requests.
        """
        # Send a series of identical requests and measure response times
        num_samples = 20
        response_times = []
        errors = 0
        
        try:
            for i in range(num_samples):
                status, response_time, size, error = self._send_request(i)
                
                if status == 200:
                    response_times.append(response_time)
                    self.logger.debug(f"Request {i+1}: Response time {response_time:.4f}s")
                else:
                    errors += 1
                    self.logger.debug(f"Request {i+1}: Failed with status {status} - {error if error else 'No error details'}")
            
            # At least 50% of requests must be successful for meaningful analysis
            min_required = max(5, int(num_samples * 0.5))
            
            if len(response_times) < min_required:
                self.assert_true(False, 
                             f"Too few successful requests ({len(response_times)}/{num_samples}) for consistency test, minimum {min_required} required")
                return
            
            # Analyze response time consistency
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            # Calculate standard deviation to measure consistency
            stdev = statistics.stdev(response_times) if len(response_times) > 1 else 0
            # Coefficient of variation (relative standard deviation)
            cv = (stdev / avg_time) * 100 if avg_time > 0 else 0
            
            # Log response time statistics
            self.logger.debug(f"Response time statistics:")
            self.logger.debug(f"  Average: {avg_time:.4f}s")
            self.logger.debug(f"  Median:  {median_time:.4f}s")
            self.logger.debug(f"  Min:     {min_time:.4f}s")
            self.logger.debug(f"  Max:     {max_time:.4f}s")
            self.logger.debug(f"  Range:   {max_time - min_time:.4f}s")
            self.logger.debug(f"  Std Dev: {stdev:.4f}s")
            self.logger.debug(f"  CV:      {cv:.1f}%")
            
            # Check coefficient of variation - still permissive but not excessive
            self.assert_true(cv < 60, f"Response time variability too high: CV={cv:.1f}%")
            
            # Check max/min ratio - should be within reasonable bounds
            if min_time > 0:
                max_min_ratio = max_time / min_time
                self.assert_true(max_min_ratio < 8, 
                              f"Response time range too wide: max/min={max_min_ratio:.1f}x")
                
        except Exception as e:
            self.logger.debug(f"Error during response time consistency test: {e}")
            self.assert_true(False, f"Response time consistency test failed: {e}")
