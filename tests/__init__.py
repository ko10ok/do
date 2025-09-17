"""Test package initialization."""

import os
import sys

# Add the parent directory to sys.path so we can import doq
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
