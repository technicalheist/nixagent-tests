"""
tests/THIN-19.py
────────────────
Self-contained multi-agent pipeline for Jira ticket THIN-19.
All constants, prompts, agent factories, and pipeline logic live here.

Run:
    .venv\Scripts\python.exe tests\THIN-19.py
"""

import sys
# Force UTF-8 output — prevents cp1252 UnicodeEncodeError on Windows
# when printing box-drawing / emoji characters in banner/section lines.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import os
from dotenv import load_dotenv
from nixagent import Agent

load_dotenv()

# ═══════════════════════════════════════════════════════════════════
# PIPELINE SETTINGS
# ═══════════════════════════════════════════════════════════════════
TEST_ID        = "THIN-19"
MAX_ITERATIONS = 5               # Max dev→test feedback loops before giving up

# ═══════════════════════════════════════════════════════════════════
# PATHS  (all derived from the repo root — works from any cwd)
# ═══════════════════════════════════════════════════════════════════
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

TICKETS_DIR     = os.path.join(BASE_DIR, "public", "tickets")
TESTS_DIR       = os.path.join(BASE_DIR, "public", "projects", "tests")
REPORTS_DIR     = os.path.join(BASE_DIR, "public", "report")
CODE_REVIEW_DIR = os.path.join(BASE_DIR, "public", "code-review")

TICKET_FILE  = os.path.join(TICKETS_DIR,     f"{TEST_ID}.md")
REPORT_FILE  = os.path.join(REPORTS_DIR,     f"{TEST_ID}.md")
REVIEW_FILE  = os.path.join(CODE_REVIEW_DIR, f"{TEST_ID}.md")
SPEC_FILE    = os.path.join(TESTS_DIR,       f"{TEST_ID}.spec.js")

JIRA_CLI_DOCS_DIR        = os.path.join(BASE_DIR, "docs", "jira-cli")
AGENT_BROWSER_SKILL_FILE = os.path.join(BASE_DIR, "docs", "agent-browser", "SKILL.md")
PLAYWRIGHT_PROJECT_DIR   = os.path.join(BASE_DIR, "public", "projects")

# Ensure all output directories exist
for _dir in [TICKETS_DIR, TESTS_DIR, REPORTS_DIR, CODE_REVIEW_DIR]:
    os.makedirs(_dir, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════
# SHARED SAFETY DIRECTIVE  (injected into every agent's system prompt)
# ═══════════════════════════════════════════════════════════════════
SHELL_SAFETY_DIRECTIVE = """
⚠️  CRITICAL SHELL COMMAND RULES — apply to EVERY shell command you execute:
- ALL shell commands MUST be compatible with PowerShell ONLY. Do NOT use bash, sh, cmd, or Unix-style syntax.
- NEVER run any command that blocks or hangs indefinitely
  (e.g. interactive prompts, watch, tail -f, npx serve, npm start).
- ALWAYS add a timeout flag when available (--timeout, --max-time, etc.).
  The built-in execute_shell_command timeout is 120 seconds — stay well within it.
- If a command needs user input or a TTY, use -y / --yes / --no-interactive instead.
- Chain multiple commands with `;` (PowerShell). NEVER use `&&`.
- If a command times out, record the failure and move on — never retry the same hanging command.
"""

# ═══════════════════════════════════════════════════════════════════
# AGENT SYSTEM PROMPTS
# ═══════════════════════════════════════════════════════════════════

JIRA_AGENT_PROMPT = f"""You are JiraAgent. Your ONLY job is to fetch a Jira ticket and save it to disk.

## Check first — skip if already done
If the file already exists at:
    {TICKET_FILE}
immediately reply with "TICKET_EXISTS" and stop — do not call any tools.

## If the file does NOT exist
1. Read the Jira CLI documentation at: {JIRA_CLI_DOCS_DIR}
2. Fetch the Jira ticket {TEST_ID} using the Jira CLI tool.
3. Save the complete ticket content to: {TICKET_FILE}
4. Reply with "TICKET_SAVED" followed by a short summary of the ticket
   (title, description, acceptance criteria).

## You are DONE after saving the file. Do NOT delegate or mention any other agent.
{SHELL_SAFETY_DIRECTIVE}"""


DEVELOPER_AGENT_PROMPT = f"""You are DeveloperAgent. You write production-ready Playwright JS automation tests.

## ══ HARD RULE — READ BEFORE ANYTHING ELSE ══════════════════════════════════
Every agent-browser command MUST be its own separate execute_shell_command call.
NEVER chain agent-browser commands with `;` or any other separator in one call.

  ❌ FORBIDDEN (causes hang):
     execute_shell_command("agent-browser open <url> ; agent-browser wait 3000 ; agent-browser snapshot -i")

  ✅ CORRECT — four separate calls (always close first to reset stale daemon):
     execute_shell_command("agent-browser close")
     execute_shell_command("agent-browser open <url> --wait-until commit")
     execute_shell_command("agent-browser wait 3000")
     execute_shell_command("agent-browser snapshot -i")

Violating this rule causes the entire pipeline to hang indefinitely.
═══════════════════════════════════════════════════════════════════════════════

## ── STEP 0: Check — skip if code already exists ────────────────────────────
List the files inside: {TESTS_DIR}
If a file prefixed with "{TEST_ID}" already exists, reply with "CODE_EXISTS" and stop.

## ── STEP 1 (MANDATORY FIRST STEP): Read the Jira Ticket ───────────────────
Read the ticket file:
    {TICKET_FILE}
You MUST completely understand the following before proceeding:
- The target URL(s) to visit
- All required input data (credentials, form values, test data)
- Every acceptance criterion and the exact steps to automate
Do NOT assume any test data — every value must come directly from the ticket.

## ── STEP 2 (MANDATORY): Read the agent-browser Skill Docs ─────────────────
Before writing a single line of test code, read the agent-browser documentation:
    {AGENT_BROWSER_SKILL_FILE}
This is non-negotiable. You must understand the tool before using it.

## ── STEP 3 (MANDATORY): Discover Real Locators via agent-browser ───────────
You MUST use agent-browser to navigate the live page and capture the actual
element refs. Do NOT guess or invent locators.
Each sub-step below is a SEPARATE execute_shell_command call:

  a) execute_shell_command("agent-browser close")
     ALWAYS run this first — kills any stale daemon left over from a previous
     iteration or timed-out command. Ignore any error output from this call.

  b) execute_shell_command("agent-browser open <URL-FROM-TICKET> --wait-until commit")
     Use `--wait-until commit` — this returns as soon as the HTTP response is received
     without waiting for the load event (which never fires on modern SPAs and causes a hang).

  c) execute_shell_command("agent-browser wait 3000")

  d) execute_shell_command("agent-browser snapshot -i")
     Study the output carefully: note every @eN ref, its type, placeholder,
     label, id, and name. These refs are your locators.

  e) For each interaction (fill or click), one call each:
     execute_shell_command("agent-browser fill @eN \\"value-from-ticket\\"")
     execute_shell_command("agent-browser click @eN")

  f) After any navigation or DOM change:
     execute_shell_command("agent-browser wait 3000")
     execute_shell_command("agent-browser snapshot -i")
     Refs are invalidated after navigation — always re-snapshot before using new refs.

  g) execute_shell_command("agent-browser screenshot")

  h) execute_shell_command("agent-browser close")

## ── STEP 4: Write the Playwright JS Test ───────────────────────────────────
Using ONLY the real locators discovered in STEP 3, write a robust Playwright test.

- Save the file to: {SPEC_FILE}
- Name `describe` and `test` blocks based solely on what the ticket describes.
- Cover ALL acceptance criteria from the ticket.
- Wrap every locator interaction in try/catch with a CSS/XPath fallback.
- Use `page.waitForURL` or `page.waitForSelector` for post-action assertions.
- The test must be runnable with:
      npx playwright test {SPEC_FILE} --timeout 60000
  (run from: {PLAYWRIGHT_PROJECT_DIR})
- Reply with "CODE_WRITTEN" when the file is saved.

## ⚠️ agent-browser CRITICAL RULES
- Call `agent-browser` directly — NEVER `npx agent-browser` (npx stays attached and hangs).
- ALWAYS run `agent-browser close` as the VERY FIRST command before any `open`. This kills any
  stale daemon left over from a previous run or timed-out iteration. Ignore errors.
- ALWAYS use `--wait-until commit` with `agent-browser open` to prevent the command from blocking
  on modern SPAs that never fire the `load` event:
      ✅ agent-browser open <url> --wait-until commit
      ❌ agent-browser open <url>   ← hangs indefinitely on SPAs
- NEVER use `agent-browser wait --load networkidle` — it hangs forever on modern web apps.
  Always use `agent-browser wait <ms>` (e.g. `agent-browser wait 3000`).
- Do NOT chain agent-browser commands. One command = one execute_shell_command call.
- Always call `agent-browser close` when all browser tasks are done.

## Constraints
- Do NOT write README or documentation files.
- Do NOT touch: {PLAYWRIGHT_PROJECT_DIR}/playwright.config.js
- ALL test files MUST be written inside: {TESTS_DIR}
- Do NOT reference or call any other agent — the pipeline manages all handoffs.
{SHELL_SAFETY_DIRECTIVE}"""


TESTER_AGENT_PROMPT = f"""You are TesterAgent. Your ONLY job is to run the Playwright test and report results.

## Check first — skip if report already exists
If the report file already exists at: {REPORT_FILE}
reply with "REPORT_EXISTS" and stop.

## How to find and run the test (PowerShell)
1. List the test files inside {TESTS_DIR} and find the file prefixed with "{TEST_ID}".
2. Run it from the Playwright project directory:
       Set-Location '{PLAYWRIGHT_PROJECT_DIR}' ; npx playwright test tests/<discovered-spec-filename> --timeout 60000
   Replace <discovered-spec-filename> with the actual file name you found.

## On PASS
1. Reply with exactly: PASS
2. Write a detailed Markdown report to: {REPORT_FILE}
   Include: test date/time, ticket ID, spec file name, result (PASSED ✅),
   tests run/passed/failed, duration, and any notable observations.

## On FAIL
1. Reply with exactly: FAIL
2. Include the FULL terminal error output (do not truncate).
3. Explain precisely WHY each failure occurred.
4. List explicit, actionable fix instructions for the developer.

## Do NOT fix the code yourself. The pipeline hands your feedback to the developer.
{SHELL_SAFETY_DIRECTIVE}"""


CODE_REVIEWER_AGENT_PROMPT = f"""You are CodeReviewerAgent. Your ONLY job is to review the completed test code.

## Check first — skip if review already exists
If the review file already exists at: {REVIEW_FILE}
reply with "REVIEW_EXISTS" and stop.

## If no review exists
1. Read the test file(s) inside: {TESTS_DIR}
2. Write a thorough, insightful code review to: {REVIEW_FILE}
   Cover: code quality, locator robustness, error handling, assertions, maintainability.
3. Reply with "REVIEW_COMPLETE".

## Do NOT run any tests or modify any code.
{SHELL_SAFETY_DIRECTIVE}"""


# ═══════════════════════════════════════════════════════════════════
# AGENT FACTORIES
# Each function builds a fresh, isolated Agent — no knowledge of
# other agents. The Python pipeline passes all context explicitly.
# ═══════════════════════════════════════════════════════════════════

def make_jira_agent() -> Agent:
    return Agent(name="JiraAgent",        verbose=True, system_prompt=JIRA_AGENT_PROMPT)

def make_developer_agent() -> Agent:
    return Agent(name="DeveloperAgent",   verbose=True, system_prompt=DEVELOPER_AGENT_PROMPT)

def make_tester_agent() -> Agent:
    """Always creates a fresh TesterAgent — no stale context from prior iterations."""
    return Agent(name="TesterAgent",      verbose=True, system_prompt=TESTER_AGENT_PROMPT)

def make_code_reviewer_agent() -> Agent:
    return Agent(name="CodeReviewerAgent",verbose=True, system_prompt=CODE_REVIEWER_AGENT_PROMPT)


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def banner(text: str) -> None:
    line = "=" * 70
    print(f"\n{line}\n  {text}\n{line}")

def section(text: str) -> None:
    print(f"\n{'─' * 60}\n  {text}\n{'─' * 60}")


# ═══════════════════════════════════════════════════════════════════
# PIPELINE ORCHESTRATOR
# Agents run sequentially. Outputs are passed as plain Python strings.
# Agents have zero knowledge of each other.
# ═══════════════════════════════════════════════════════════════════

def main():
    banner(f"Multi-Agent Web Testing Pipeline  |  Ticket: {TEST_ID}")
    print(f"  Ticket file : {TICKET_FILE}")
    print(f"  Spec file   : {SPEC_FILE}")
    print(f"  Report file : {REPORT_FILE}")
    print(f"  Review file : {REVIEW_FILE}")

    # ── STEP 1: JiraAgent ────────────────────────────────────────────────────
    section("STEP 1 — JiraAgent: fetch Jira ticket")
    jira_agent  = make_jira_agent()
    jira_result = jira_agent.run(
        f"Fetch and save Jira ticket {TEST_ID} following your instructions."
    )
    print("\n[Pipeline] JiraAgent done.")

    # ── STEP 2: DeveloperAgent (initial code write) ──────────────────────────
    section("STEP 2 — DeveloperAgent: discover locators & write Playwright test")
    dev_agent = make_developer_agent()
    dev_agent.run(
        f"The Jira ticket for {TEST_ID} has been fetched.\n"
        f"JiraAgent summary:\n{jira_result}\n\n"
        f"Follow your instructions: check for existing code, then write the test."
    )
    print("\n[Pipeline] DeveloperAgent done with initial pass.")

    # ── STEP 3: Dev / Test iteration loop ────────────────────────────────────
    test_passed = False
    for iteration in range(1, MAX_ITERATIONS + 1):
        section(f"STEP 3 — TesterAgent (iteration {iteration}/{MAX_ITERATIONS})")

        tester_agent  = make_tester_agent()   # fresh agent every iteration
        tester_result = tester_agent.run(
            f"Run the Playwright test for {TEST_ID} following your instructions."
        )

        if "PASS" in tester_result and "FAIL" not in tester_result.upper()[:20]:
            print(f"\n[Pipeline] ✅ Tests PASSED on iteration {iteration}!")
            test_passed = True
            break

        if iteration == MAX_ITERATIONS:
            print(f"\n[Pipeline] ⚠️  Reached max iterations ({MAX_ITERATIONS}) without PASS.")
            break

        # Feed failure details back into the developer's existing conversation
        section(f"STEP 3 — DeveloperAgent fixing failures (iteration {iteration})")
        dev_agent.run(
            f"The TesterAgent ran your Playwright test and it FAILED.\n\n"
            f"Failure details:\n{tester_result}\n\n"
            f"Fix the test at {SPEC_FILE} based on the feedback above. "
            f"Do NOT explain — just apply the fix and print CODE_WRITTEN when done."
        )

    # ── STEP 4: CodeReviewerAgent ─────────────────────────────────────────────
    section("STEP 4 — CodeReviewerAgent: final code review")
    reviewer_agent = make_code_reviewer_agent()
    reviewer_agent.run(
        f"The Playwright test for {TEST_ID} has been written"
        f"{' and tests passed' if test_passed else ' (tests may have failed)'}. "
        f"Follow your instructions to review the code."
    )
    print("\n[Pipeline] CodeReviewerAgent done.")

    # ── DONE ──────────────────────────────────────────────────────────────────
    banner("PIPELINE COMPLETE")
    print(f"  Ticket   → {TICKET_FILE}")
    print(f"  Spec     → {SPEC_FILE}")
    print(f"  Report   → {REPORT_FILE}")
    print(f"  Review   → {REVIEW_FILE}")
    print()


if __name__ == "__main__":
    main()
