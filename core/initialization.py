#!/usr/bin/env python3
"""
Initialization Module for Webserv Tester

Handles environment setup and verification of required directories and files.
This module ensures all necessary components are in place before tests are run.
"""

import os
import sys
import importlib.util
import subprocess
import logging
from pathlib import Path

# Constants for directory structure
DIRS_TO_CREATE = ["logs", "tests_suites"]
REQUIRED_PACKAGES = ["requests", "psutil"]

# Essential directories that must exist but don't need specific files checked
ESSENTIAL_DIRS = ["data/uploads"]

# Required files (implies their parent directories must exist)
REQUIRED_FILES = [
    "data/conf/test.conf",
    "data/www/index.html",
    "data/www/404.html",
    "data/www/static/.gitkeep"  # Empty file to ensure static directory exists
]

class InitializationError(Exception):
    """Exception raised for initialization errors."""
    pass

def get_tester_root():
    """Get the absolute path to the tester root directory (parent of core)."""
    core_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    return core_dir.parent

def check_and_create_directories():
    """Create required directories and check that essential directories exist."""
    tester_root = get_tester_root()
    
    # Create directories that should be created automatically
    for dir_path in DIRS_TO_CREATE:
        full_path = tester_root / dir_path
        if not full_path.exists():
            print(f"Creating directory: {full_path}")
            full_path.mkdir(parents=True, exist_ok=True)
    
    # Check essential directories that must exist
    missing_dirs = []
    for dir_path in ESSENTIAL_DIRS:
        full_path = tester_root / dir_path
        if not full_path.exists():
            missing_dirs.append(str(full_path))
    
    if missing_dirs:
        raise InitializationError(
            f"Missing essential directories: {', '.join(missing_dirs)}.\n"
            "These directories are required for testing."
        )
    
    # Create __init__.py files for Python packages
    for package_dir in ["tests_suites"]:
        init_file = tester_root / package_dir / "__init__.py"
        if not init_file.exists():
            init_file.touch()
    
    return True

def check_and_install_packages():
    """Check if required Python packages are installed, install them if not."""
    missing_packages = []
    
    for package in REQUIRED_PACKAGES:
        if importlib.util.find_spec(package) is None:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Installing missing packages: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            print("Dependencies installed successfully.")
            return True
        except subprocess.CalledProcessError:
            print("WARNING: Failed to install dependencies automatically.")
            print(f"Please manually install: {', '.join(missing_packages)}")
            print("You can install them using: pip install -r requirements.txt")
            return False
    
    return False

def check_test_files():
    """Check if required test files exist and are not empty."""
    tester_root = get_tester_root()
    
    for file_path_str in REQUIRED_FILES:
        file_path = tester_root / file_path_str
        
        # Special handling for .gitkeep files - always create them if missing
        if file_path.name == '.gitkeep':
            # Create parent directory if needed
            if not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create the .gitkeep file if it doesn't exist
            if not file_path.exists():
                file_path.touch()
            
            # Continue to next file
            continue
            
        # For regular files, check if parent directory exists
        if not file_path.parent.exists():
            raise InitializationError(f"Directory for required file not found: {file_path.parent}")
        
        # Check if regular file exists
        if not file_path.exists():
            raise InitializationError(f"Required file not found: {file_path}")
        
        # Check if regular file is empty
        if file_path.stat().st_size == 0:
            raise InitializationError(f"Required file is empty: {file_path}")

def update_cgi_handlers():
    """Update CGI handler paths in the test configuration file."""
    try:
        # Import here to avoid circular imports
        from core.cgi_resolver import CGIResolver
        
        # Update CGI handlers in the configuration file
        resolver = CGIResolver()
        return resolver.update_config()
    except ImportError:
        print("WARNING: CGI resolver not available")
        return False
    except Exception as e:
        print(f"ERROR: Failed to update CGI handlers: {e}")
        return False

def initialize_environment():
    """Initialize the testing environment."""
    try:
        # Check required directories
        check_and_create_directories()
        
        # Check and install required packages
        packages_installed = check_and_install_packages()
        
        # Check required test files
        check_test_files()
        
        # Update CGI handlers in the test configuration file
        update_cgi_handlers()
        
        return True
        
    except InitializationError as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    # If this file is run directly, initialize the environment
    if not initialize_environment():
        sys.exit(1)