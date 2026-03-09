import os
import sys
import glob
import subprocess

# Dynamically add the parent lib/ directory to sys.path
lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from helpers.utils import setup_stdout_encoding, banner
from config import REPORTS_DIR, get_shell_safety_directive
from nixagent import Agent

def run_all_tests():
    """Run each test separately."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Find all THIN-*.py files (or any test files avoiding this script)
    test_files = [f for f in glob.glob(os.path.join(current_dir, "*.py")) if os.path.basename(f) != "run_all_test.py" and not os.path.basename(f).startswith("__")]
    test_files.sort()

    for test_file in test_files:
        test_name = os.path.basename(test_file)
        banner(f"Running test separately: {test_name}")
        # Execute the test script
        result = subprocess.run([sys.executable, test_file])
        if result.returncode != 0:
            print(f"Warning: {test_name} failed with return code {result.returncode}")
        print(f"Finished {test_name}\n")

def consolidate_reports():
    """Run an AI agent to consolidate the generated reports."""
    banner("Consolidating reports via AI Agent")
    
    consolidated_file = os.path.join(REPORTS_DIR, 'consolidated_report.md')
    
    system_prompt = f"""You are the ConsolidatorAgent.
Your job is to read all the individual test reports and produce a single, well-structured, merged consolidated report.

{get_shell_safety_directive()}

Instructions:
1. List all the .md report files (e.g. THIN-*.md) in the {REPORTS_DIR} directory.
   Skip '{os.path.basename(consolidated_file)}' if it already exists.
2. Read the contents of each report file carefully.
3. Consolidate them into a single comprehensive Markdown file. Summarize successes, failures, and overall trends.
4. Save the final consolidated report to: {consolidated_file}
5. Reply with "CONSOLIDATION_COMPLETE" once the file is fully written.
"""

    agent = Agent(
        name="ConsolidatorAgent",
        verbose=True,
        system_prompt=system_prompt
    )
    
    response = agent.run(
        "Please perform your step-by-step instructions to read all test reports and create a consolidated report.",
        max_iterations=20
    )
    print("\n--- Consolidator Agent Response ---")
    print(response)

if __name__ == "__main__":
    setup_stdout_encoding()
    run_all_tests()
    consolidate_reports()
