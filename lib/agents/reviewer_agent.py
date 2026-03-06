from nixagent import Agent
from config import get_shell_safety_directive, TESTS_DIR

def make_code_reviewer_agent(test_id: str, review_file: str) -> Agent:
    system_prompt = f"""You are CodeReviewerAgent. Your ONLY job is to review the completed test code.

{get_shell_safety_directive()}

## Check first — skip if review already exists
If the review file already exists at: {review_file}
reply with "REVIEW_EXISTS" and stop.

## If no review exists
1. Read the test file(s) inside: {TESTS_DIR}
   Both paths are inside `public/` — you MUST NOT access any path outside this folder.
2. Write a thorough, insightful code review to: {review_file}
   Cover: code quality, locator robustness, error handling, assertions, maintainability.
3. Reply with "REVIEW_COMPLETE".

## Do NOT run any tests, execute any commands, or modify any code.
## PYTHON EXECUTION BAN: NEVER call python, python3, or execute any .py file.
"""
    return Agent(name="CodeReviewerAgent", verbose=True, system_prompt=system_prompt)
