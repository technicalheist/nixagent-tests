from nixagent import Agent
from config import get_shell_safety_directive, TESTS_DIR

def make_code_reviewer_agent(test_id: str, review_file: str, ticket_file: str, report_file: str) -> Agent:
    system_prompt = f"""You are CodeReviewerAgent. Your ONLY job is to review the completed test code.

{get_shell_safety_directive()}

## Check first — skip if review already exists
If the review file already exists at: {review_file}
reply with "REVIEW_EXISTS" and stop.

## If no review exists
1. Information Gathering:
   - Read the test file(s) inside: {TESTS_DIR}
   - Read the Jira Ticket requirements inside: {ticket_file}
   - Read the Tester report inside: {report_file}
   If the tester report is not found, you MUST instruct the pipeline that a report does not exist yet.
   All paths are inside `public/` — you MUST NOT access any path outside this folder.

2. Writing the Review:
   Write a thorough, insightful, and SPECIFIC code review to: {review_file}
   The review MUST contain the code review as well as requirement checks based on the Jira ticket and the Tester report.
   Cover: code quality, locator robustness, error handling, assertions, maintainability, and alignment with requirements.

   FAILED TEST CONDITION:
   If the Tester report indicates that the test FAILED, you MUST add the following exact sentence prominently at the top of your review:
   "⚠️ **Human intervention is required: The automated testing failed to pass all criteria.**"

3. Reply with "REVIEW_COMPLETE".

## Do NOT run any tests, execute any commands, or modify any code.
## PYTHON EXECUTION BAN: NEVER call python, python3, or execute any .py file.
"""
    from helpers.token_calculator import with_token_calculator, get_token_report
    import os
    
    agent = Agent(name="CodeReviewerAgent", verbose=True, system_prompt=system_prompt)
    agent = with_token_calculator(agent)
    
    original_run = agent.run
    def wrapped_run(*args, **kwargs):
        res = original_run(*args, **kwargs)
        
        # After the reviewer agent finishes writing its review, append the clean recent token report 
        if os.path.exists(review_file):
            with open(review_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Remove any previously appended token report to avoid duplication during test retries
            content = content.split("📊 Token Usage & Cost Report 📊")[0].strip()
            
            with open(review_file, "w", encoding="utf-8") as f:
                if content:
                    f.write(content + "\n\n")
                f.write(get_token_report())
        else:
            with open(review_file, "w", encoding="utf-8") as f:
                f.write(get_token_report())
            
        return res
        
    agent.run = wrapped_run
    return agent
