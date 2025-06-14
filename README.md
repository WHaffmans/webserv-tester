<h1 align="center">
	Webserv Testing Framework
</h1>
<p align="center">
	This project helped you? Give it a 🌟!
</p>

## 🚀 Quick Start

The easiest way to run tests is to simply execute the script. You can change tester options by editing variables at the top of the script.

```bash
./tests/run_test.sh
```

## 🔧 Installation

Clone this repository as a submodule of your webserv project:

```bash
git submodule add https://github.com/ulyssegerkens/webserv-tester.git tests
```

The framework is designed to be self-initializing. Just running the test script will init the environment, install dependencies, and detect CGI interpreters automatically.

## ⚙️ Command-line Options
If you want to run tests directly from the Python script (instead of the shell script), you can use the command-line interface:

```
usage: run_tests.py [-h] [--server-path SERVER_PATH] [--host HOST]
                    [--timeout TIMEOUT]
                    [--suite {basic,invalid,config,http,method,upload,cgi,edge,error,security,performance,all}]
                    [--test TEST] [--startup-delay STARTUP_DELAY]
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

> **Warning**: A lot of tests have been written with LLM and may contain some errors. Please **review tests carefully**. They could also be too permissive and return false positives.

> **Warning**: Tests are relatively **strict**. A lot of them are not asked in the subject. They are here to help you to implement a robust server. For example, the `InvalidConfigFileTests` ask for quite precise error log messages.

> **Warning**: This tester is designed to run webserv in a controlled **environment** with the specific configuration file (`data/conf/test.conf`) and dedicated server files directory (`data/`).

## 📊 Logging

The framework provides detailed logging:

- Console output: Concise test results with colorful indicators
- List of fails: Separate log files for failed tests with details
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

## Contributing

Contributions for adding new tests, improving existing ones, or enhancing the framework itself are welcome! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute.