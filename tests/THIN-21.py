"""
tests/THIN-21.py
────────────────
Executes the test pipeline for THIN-19.
"""

import os
import sys

# Dynamically add the parent lib/ directory to sys.path
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from helpers.utils import setup_stdout_encoding
from pipelines.automated_test_generator import automatedTestGenerator

if __name__ == "__main__":
    setup_stdout_encoding()
    automatedTestGenerator("THIN-21", max_iterations=10)
