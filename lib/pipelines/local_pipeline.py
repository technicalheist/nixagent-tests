import os
from config import get_test_paths
from helpers.utils import banner
from agents.jira_agent import make_jira_agent
from agents.browser_agent import make_browser_agent
from agents.developer_agent import make_developer_agent
from agents.tester_agent import make_tester_agent
from agents.reviewer_agent import make_code_reviewer_agent

def local_programmatic_pipeline(test_id: str, max_iterations: int = 5):
    """
    Programmatic Test Generator Pipeline.
    Runs the agents in a strictly controlled Python loop, rather than
    relying on an AI Coordinator to orchestrate them.
    This eliminates AI-to-AI context-loss flakiness.
    """
    paths = get_test_paths(test_id)
    ticket_file = paths["ticket_file"]
    report_file = paths["report_file"]
    review_file = paths["review_file"]
    spec_file = paths["spec_file"]
    locator_file = paths["locator_file"]

    banner(f"Programmatic Local Pipeline | Ticket: {test_id}")
    print(f"  Ticket file : {ticket_file}")
    print(f"  Spec file   : {spec_file}")
    print(f"  Report file : {report_file}")
    print(f"  Review file : {review_file}")
    print(f"  Locator file: {locator_file}")

    # Build the specialized sub-agents
    jira_agent = make_jira_agent(test_id, ticket_file)
    browser_agent = make_browser_agent(test_id, ticket_file, locator_file)
    dev_agent = make_developer_agent(test_id, ticket_file, spec_file, locator_file)
    tester_agent = make_tester_agent(test_id, report_file, spec_file)
    reviewer_agent = make_code_reviewer_agent(test_id, review_file, ticket_file, report_file)

    # 1. Jira Agent: fetch the ticket
    print("\n[Pipeline] Step 1: Fetching Jira Ticket...")
    if not os.path.exists(ticket_file):
        jira_agent.run(f"Fetch the Jira ticket {test_id} and save it.", max_iterations=max_iterations)
    else:
        print(f"[Pipeline] Ticket {ticket_file} already exists. Skipping.")

    # 2. Browser Agent: get the locators and save in locators
    print("\n[Pipeline] Step 2: Generating Locators...")
    if not os.path.exists(spec_file):
        browser_agent.run(f"Navigate the ticket's URL(s), discover locators, and save to {locator_file}.", max_iterations=max_iterations)
    else:
        print(f"[Pipeline] Spec already exists. Skipping Locator discovery.")

    # 3. Developer Agent: Write the actual initial code
    print("\n[Pipeline] Step 3: Writing Playwright Code...")
    if not os.path.exists(spec_file):
        dev_agent.run(f"Read {locator_file} and write the Playwright test.", max_iterations=max_iterations)
    else:
        print(f"[Pipeline] Spec already exists. Skipping initial Code Writer.")

    # 4 & 5 & 6. Tester & Developer Feedback Loop
    print("\n[Pipeline] Step 4: Testing & Feedback Loop...")
    for i in range(max_iterations):
        print(f"\n   --- Feedback Loop Iteration {i+1} / {max_iterations} ---")
        
        # Tester agent runs the code
        tester_response = tester_agent.run(f"Run the test {spec_file} and generate the report.", max_iterations=max_iterations)
        
        # Programmatic parsing of the AI's output
        if "PASS" in tester_response:
            print("[Pipeline] Tests Passed! Breaking out of feedback loop.")
            break
        elif "FAIL" in tester_response:
            print("[Pipeline] Tests Failed. Handing trace back to Developer Agent...")
            dev_agent.run(
                f"The tests failed. Here is the full output from the Tester:\n\n{tester_response}\n\nPlease fix the code and explicitly overwrite {spec_file}.",
                max_iterations=max_iterations
            )
        else:
            print("[Pipeline] Unknown response from TesterAgent. Breaking loop for safety.")
            break

    # 7. Code Reviewer: Create the final review
    print("\n[Pipeline] Step 5: Final Code Review...")
    reviewer_agent.run("Write the final review and ensure it incorporates the report feedback.", max_iterations=max_iterations)

    banner("PIPELINE COMPLETE")
    print(f"Programmatic pipeline for {test_id} has finished.")
