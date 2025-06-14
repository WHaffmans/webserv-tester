# Webserv Testing Framework

Build ***to test & debug*** your webserv implementation.

## 🚀 Quick Start

The easiest way to run tests is to simply execute the script. You can change tester options by editing variables at the top of the script.

```bash
./run_test.sh
```

## 🔧 Installation

The framework is designed to be self-initializing. Just running the test script will:

1. Create necessary directories if they don't exist
2. Install required Python dependencies (`requests`, `psutil`)
3. Generate default test configuration files
4. Auto-detect and configure CGI interpreters

## 🧰 CGI Interpreter Auto-detection

The tester automatically detects available CGI interpreters on your system and updates the test configuration file:

- Supported script types: `.py`, `.php`, `.pl`, `.rb`, `.sh`, `.cgi`
- The tester searches for appropriate interpreters (python3, php, perl, etc.)
- Warnings are displayed if interpreters are missing
- You don't need to manually edit the configuration file

This ensures CGI tests work correctly on your specific environment without manual configuration.

## ⚙️ Command-line Options

```
usage: run_tests.py [-h] [--server-path SERVER_PATH] [--host HOST]
                    [--timeout TIMEOUT]
                    [--suite {basic,invalid,config,http,method,upload,cgi,edge,error,security,performance,all}]
                    [--test TEST] [--startup-delay STARTUP_DELAY]

Test the webserv HTTP server implementation
```

## 🗂️ Test Suite

Tests are organized into features suites:

- **Basic**: Fundamental server functionality (smoke tests)
- **HTTP**: HTTP protocol compliance tests
- **Config**: Configuration file parsing and application
- **Edge**: Edge cases and boundary testing
- **Method**: HTTP methods (GET, POST, etc.) implementation
- **CGI**: Common Gateway Interface functionality
- **Upload**: File upload handling
- **Security**: Security features and vulnerability testing
- **Performance**: Load and performance testing
- **Error**: Error handling and custom error pages

> **Warning**: A lot of tests have been written with LLM and may contain some errors. Please review them carefully. They could also be too permissive and return false positives.

> **Warning**: Tests are relatively strict. A lot of them are not asked in the subject. They are here to help you to implement a robust server. For example, the `InvalidConfigFileTests` ask for quite precise error log messages.

## ⚠️ Controlled Testing Environment
> **Important:** This tester is designed to run webserv in a controlled environment with the specific configuration file (`data/conf/test.conf`) and dedicated server files directory (`data/`). It is not intended for testing independent deployments. The tester directly manages the webserv executable, its configuration, and tested data.

The tests are specifically designed to work with the provided `test.conf` configuration file and will verify that your server correctly implements the features as specified in this configuration.

## 📊 Logging

The framework provides detailed logging:

- Console output: Concise test results with colorful indicators
- Failed tests: Separate log files for failed tests with details
- Log files: Detailed information stored in `logs/` directory
- Test source code: For single test runs, the test source code is included in the logs for easier debugging

**Warning**: `run_test.sh` removes all previous logs before running tests. This can be disabled by setting `CLEAN_LOGS=false` in the script.

## 🔍 Fixing a Test
The tester has been designed to be used as:
1. Running a test suite with `run_test.sh`
2. Choose a test to fix, copy its name from the "Failed tests" logs
3. Run the test independently by copying the test name in `run_test.sh`
4. Analyze logs in logs file. The test implementation source code is also included in log to check if it is well implemented and to have a better understanding of why it failed
5. Fix the bug in your webserv implementation

## ✏️ Writing New Tests

1. Create a new test class in `tests_suites/` or add to an existing one
2. Test methods must start with `test_`
3. Use assertions provided by the TestCase class
4. Group related tests in the same class

Example test:

```python
from core.test_case import TestCase

class MyTests(TestCase):
    """
    Tests specific to the configuration in test.conf:
    location / {
        index index.html;
        methods GET POST;
    }
    """

    def test_my_feature(self):
        """Test description here."""
        response = self.runner.send_request('GET', '/my-endpoint')
        self.assert_equals(response.status_code, 200)
        self.assert_true('Content-Type' in response.headers)
```

## Contributing

List of features to implement, in priority order:
- Add a file where user can specify a list of tests to ignore (for the server feature he don't want to implement).
- Add RFC references to tests
- Check test implementation
- Add 2 test modes: strict (RFC/nginx-like) and permissive (subject/correction)
- Improve test coverage
- Refactor test framework