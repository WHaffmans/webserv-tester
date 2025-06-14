#!/usr/bin/env python3
"""
CGI Resolver Module

Automatically detects available interpreters for CGI scripts and updates the test.conf file.
Raises warnings if appropriate interpreters aren't found on the system.
"""

import os
import sys
import shutil
import re
from pathlib import Path
import logging
from core.logger import get_logger

class CGIResolver:
    """Finds and configures CGI interpreters for the webserver tests."""
    
    # Map of file extensions to possible interpreter binaries
    # To add support for a new interpreter:
    # 1. Add an entry for the file extension (e.g., '.js')
    # 2. List the possible interpreter binaries in order of preference (e.g., ['node', 'nodejs'])
    # 3. The resolver will use the first interpreter found on the system
    CGI_EXTENSIONS = {
        '.py': ['python3', 'python'],
        '.php': ['php', 'php-cgi'],
        '.pl': ['perl'],
        '.rb': ['ruby'],
        '.sh': ['sh', 'bash'],
        '.cgi': []  # Binary CGI scripts don't need an interpreter
    }
    
    def __init__(self, config_path="data/conf/test.conf"):
        """
        Initialize the CGI resolver.
        
        Args:
            config_path (str): Path to the server configuration file
        """
        self.logger = get_logger()
        self.config_path = Path(config_path)
        
    def find_interpreter(self, extension):
        """
        Find the appropriate interpreter for a given file extension.
        
        Args:
            extension (str): File extension (e.g., '.py', '.php')
            
        Returns:
            str: Path to the interpreter, or None if not found
        """
        if extension.lower() not in self.CGI_EXTENSIONS:
            return None
            
        # Binary CGI scripts don't need an interpreter
        if extension.lower() == '.cgi':
            return ""
            
        # Try to find each potential interpreter
        for interpreter in self.CGI_EXTENSIONS[extension.lower()]:
            path = shutil.which(interpreter)
            if path:
                return path
                
        return None
        
    def is_valid_interpreter(self, interpreter_path):
        """
        Check if an interpreter path is valid and executable.
        
        Args:
            interpreter_path (str): Path to the interpreter
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Empty path is valid for .cgi files
        if not interpreter_path:
            return True
            
        # Check if the interpreter exists and is executable
        return os.path.isfile(interpreter_path) and os.access(interpreter_path, os.X_OK)
        
    def update_config(self):
        """
        Update the configuration file with available CGI interpreters.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.config_path.exists():
            self.logger.error(f"Configuration file not found: {self.config_path}")
            return False
            
        # Read the configuration file
        try:
            with open(self.config_path, 'r') as f:
                config_lines = f.readlines()
        except Exception as e:
            self.logger.error(f"Failed to read configuration file: {e}")
            return False
            
        # Find the CGI handler section
        cgi_section_start = -1
        cgi_section_end = -1
        
        for i, line in enumerate(config_lines):
            if re.search(r'^\s*cgi_handler\s+\.', line):
                if cgi_section_start == -1:
                    cgi_section_start = i
                cgi_section_end = i
        
        if cgi_section_start == -1:
            self.logger.error("No CGI handler directives found in configuration file")
            return False
            
        # Update each CGI handler with the appropriate interpreter
        missing_interpreters = []
        for i in range(cgi_section_start, cgi_section_end + 1):
            # Extract the extension from the line
            match = re.search(r'^\s*cgi_handler\s+(\.[\w]+)\s*(?:([^;]+)?)', config_lines[i])
            if match:
                extension = match.group(1)
                existing_interpreter = match.group(2).strip() if match.group(2) else ""
                
                # Check if existing interpreter is valid
                if existing_interpreter and self.is_valid_interpreter(existing_interpreter):
                    # Keep existing valid interpreter, just ensure it has semicolon
                    config_lines[i] = f"        cgi_handler {extension} {existing_interpreter};\n"
                    continue
                elif existing_interpreter:
                    self.logger.warning(f"Existing interpreter for {extension} is invalid: {existing_interpreter}")
                
                # Find a new interpreter
                interpreter_path = self.find_interpreter(extension)
                
                # Update the line with the interpreter path
                if interpreter_path is not None:
                    # Add semicolon at the end for nginx-style config
                    config_lines[i] = f"        cgi_handler {extension} {interpreter_path};\n"
                else:
                    missing_interpreters.append(extension)
                    self.logger.warning(f"No interpreter found for {extension} files")
                    config_lines[i] = f"        cgi_handler {extension} ;\n"
                    
        # Write the updated configuration
        try:
            with open(self.config_path, 'w') as f:
                f.writelines(config_lines)
        except Exception as e:
            self.logger.error(f"Failed to write configuration file: {e}")
            return False
            
        # Report on missing interpreters
        if missing_interpreters:
            self.logger.warning("The following CGI interpreters were not found:")
            for ext in missing_interpreters:
                suggestions = ', '.join(self.CGI_EXTENSIONS[ext])
                self.logger.warning(f"  - {ext}: Install one of: {suggestions}")
                
        return True 