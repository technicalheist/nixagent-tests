"""
tests/THIN-20.py
────────────────
Executes the test pipeline for THIN-20.
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
    
    files_to_delete = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "report", "THIN-20.md")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "code-review", "THIN-20.md"))
    ]
    
    for file_to_delete in files_to_delete:
        if os.path.exists(file_to_delete):
            try:
                os.remove(file_to_delete)
                print(f"Deleted {file_to_delete}")
            except Exception as e:
                print(f"Failed to delete {file_to_delete}: {e}")

    automatedTestGenerator("THIN-20", max_iterations=30)
