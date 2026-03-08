import os
import platform
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

TICKETS_DIR     = os.path.join(BASE_DIR, "public", "tickets")
TESTS_DIR       = os.path.join(BASE_DIR, "public", "projects", "tests")
REPORTS_DIR     = os.path.join(BASE_DIR, "public", "report")
CODE_REVIEW_DIR = os.path.join(BASE_DIR, "public", "code-review")
LOCATOR_DIR     = os.path.join(BASE_DIR, "public", "locators")

JIRA_CLI_DOCS_DIR      = os.path.join(BASE_DIR, "docs", "jira-cli")
BROWSER_USE_SKILL_FILE = os.path.join(BASE_DIR, "docs", "browser-use", "SKILL.md")
PLAYWRIGHT_PROJECT_DIR = os.path.join(BASE_DIR, "public", "projects")

# Ensure all output directories exist
for _dir in [TICKETS_DIR, TESTS_DIR, REPORTS_DIR, CODE_REVIEW_DIR, LOCATOR_DIR]:
    os.makedirs(_dir, exist_ok=True)

IS_WINDOWS  = platform.system() == "Windows"
SHELL_NAME  = "PowerShell" if IS_WINDOWS else "bash"
CMD_CHAIN   = ";" if IS_WINDOWS else "&&"
CMD_CD      = f"Set-Location '{PLAYWRIGHT_PROJECT_DIR}' ;" if IS_WINDOWS else f"cd '{PLAYWRIGHT_PROJECT_DIR}' &&"
PYTHON_EXE  = r".venv\Scripts\python.exe" if IS_WINDOWS else ".venv/bin/python"

def get_shell_safety_directive() -> str:
    return f"""CRITICAL SHELL COMMAND RULES — apply to EVERY shell command you execute:
- The system is running on: {platform.system()} — use {SHELL_NAME} syntax for ALL shell commands.
- Do NOT mix shell syntaxes. {"Bash / sh / cmd syntax is forbidden." if IS_WINDOWS else "PowerShell / cmd syntax is forbidden."}
- NEVER run any command that blocks or hangs indefinitely
  (e.g. interactive prompts, watch, tail -f, npx serve, npm start).
- ALWAYS add a timeout flag when available (--timeout, --max-time, etc.).
  The built-in execute_shell_command timeout is 120 seconds — stay well within it.
- If a command needs user input or a TTY, use -y / --yes / --no-interactive instead.
- Chain multiple commands with `{CMD_CHAIN}` ({SHELL_NAME}). {"NEVER use &&." if IS_WINDOWS else "NEVER use `;` for chaining."}
- If a command times out, record the failure and move on — never retry the same hanging command.

ABSOLUTE WORKSPACE RESTRICTION — NO EXCEPTIONS:
- You MUST only read, write, list, and execute commands inside the `public/` folder:
    {os.path.join(BASE_DIR, 'public')}
- You are STRICTLY FORBIDDEN from accessing, executing, or writing to any path outside
  of the `public/` folder, including: the repo root, `tests/`, `lib/`, `docs/`, `.agents/`,
  `.venv/`, or any other directory.
- Reading documentation files (e.g. SKILL.md) outside `public/` is ONLY allowed for
  reading — NEVER executing or writing.
- Using `cd`, `Set-Location`, or any command that changes the working directory to a path
  outside `public/` is STRICTLY FORBIDDEN.

PYTHON EXECUTION IS STRICTLY FORBIDDEN:
- You MUST NOT execute any Python scripts (.py files) under any circumstances.
- NEVER call `python`, `python3`, or `{PYTHON_EXE}` (or any Python variant).
- The pipeline is managed externally. Do NOT attempt to run or re-invoke any .py files.
- If you encounter a .py file, you may only READ its content — never execute it.
"""

def get_test_paths(test_id: str) -> dict:
    return {
        "ticket_file": os.path.join(TICKETS_DIR, f"{test_id}.md"),
        "report_file": os.path.join(REPORTS_DIR, f"{test_id}.md"),
        "review_file": os.path.join(CODE_REVIEW_DIR, f"{test_id}.md"),
        "spec_file": os.path.join(TESTS_DIR, f"{test_id}.spec.js"),
        "locator_file": os.path.join(LOCATOR_DIR, f"{test_id}.md"),
    }
