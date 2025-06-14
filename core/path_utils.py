#!/usr/bin/env python3
"""
Path Utilities

Consistent path handling for the tester framework.
"""

import os
from pathlib import Path

def get_tester_root():
    """
    Get the absolute path to the tester root directory.
    This is the parent directory of the 'core' module.
    
    Returns:
        Path: Absolute path to the tester root directory
    """
    # Find the core directory (where this file is)
    core_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    # The tester directory is the parent of core
    return core_dir.parent

def resolve_path(relative_path):
    """
    Resolve a path relative to the tester root directory.
    
    Args:
        relative_path (str): Path relative to tester root
        
    Returns:
        Path: Absolute path
    """
    return get_tester_root() / relative_path
