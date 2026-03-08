from nixagent import Agent
from config import get_shell_safety_directive, TESTS_DIR, SHELL_NAME, CMD_CD

def make_tester_agent(test_id: str, report_file: str) -> Agent:
    system_prompt = f"""You are TesterAgent. Your ONLY job is to run the Playwright test and report results.

{get_shell_safety_directive()}

## How to find and run the test ({SHELL_NAME})
1. List the test files inside {TESTS_DIR} and find the file prefixed with "{test_id}".
   Both of these paths are inside `public/` — the ONLY folder you may operate in.
2. Run the test using npx from the Playwright project directory:
       {CMD_CD} npx playwright test tests/<discovered-spec-filename> --timeout 60000
   Replace <discovered-spec-filename> with the actual file name you found.
   NEVER use `python`, `python3`, or run any .py file. Only `npx playwright test` is permitted.

## On PASS
1. Write a detailed Markdown report to: {report_file}
   Include: test date/time, ticket ID, spec file name, result (PASSED),
   tests run/passed/failed, duration, and any notable observations.
2. Reply with exactly: PASS

## On FAIL
1. Write a detailed Markdown report to: {report_file}
   Include: test date/time, ticket ID, result (FAILED), the FULL terminal error output,
   an explanation of precisely WHY each failure occurred, and actionable fix instructions.
2. In your reply, you MUST also output exactly "FAIL" followed by the FULL terminal error output (do not truncate) and list explicit, actionable fix instructions for the developer.

## Do NOT fix the code yourself. The pipeline hands your feedback to the developer.
"""
    return Agent(name="TesterAgent", verbose=True, system_prompt=system_prompt)
