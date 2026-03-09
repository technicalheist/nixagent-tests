from nixagent import Agent
from config import get_test_paths
from helpers.utils import banner
from agents.jira_agent import make_jira_agent
from agents.browser_agent import make_browser_agent
from agents.developer_agent import make_developer_agent
from agents.tester_agent import make_tester_agent
from agents.reviewer_agent import make_code_reviewer_agent

def automatedTestGenerator(test_id: str, max_iterations: int = 5):
    """
    Automated Test Generator Pipeline.
    Runs the multi-agent pipeline using native Agent collaboration tools.
    """
    paths = get_test_paths(test_id)
    ticket_file = paths["ticket_file"]
    report_file = paths["report_file"]
    review_file = paths["review_file"]
    spec_file = paths["spec_file"]
    locator_file = paths["locator_file"]

    banner(f"Automated Test Generator Pipeline | Ticket: {test_id}")
    print(f"  Ticket file : {ticket_file}")
    print(f"  Spec file   : {spec_file}")
    print(f"  Report file : {report_file}")
    print(f"  Review file : {review_file}")
    print(f"  Locator file: {locator_file}")

    # Build the specialized sub-agents
    jira_agent = make_jira_agent(test_id, ticket_file)
    browser_agent = make_browser_agent(test_id, ticket_file, locator_file)
    dev_agent = make_developer_agent(test_id, ticket_file, spec_file, locator_file)
    tester_agent = make_tester_agent(test_id, report_file)
    reviewer_agent = make_code_reviewer_agent(test_id, review_file, ticket_file, report_file)

    import os

    # Determine what assets already exist to make the Coordinator smarter
    ticket_exists = os.path.exists(ticket_file)
    spec_exists = os.path.exists(spec_file)

    # Dynamically build the Coordinator instructions
    coordinator_tasks = []
    step_num = 1

    if not ticket_exists:
        coordinator_tasks.append(f"{step_num}. Use `ask_agent_JiraAgent` to fetch Jira ticket {test_id}.")
        step_num += 1
    else:
        print(f"[Pipeline] Ticket already exists. Skipping Jira fetch step.")

    if not spec_exists:
        coordinator_tasks.append(f"{step_num}. Use `ask_agent_BrowserAgent` to navigate the ticket's URL(s), discover locators, and save the locators to {locator_file}.")
        step_num += 1
        coordinator_tasks.append(f"{step_num}. Once BrowserAgent finishes, use `ask_agent_DeveloperAgent` and instruct them to read {locator_file} and write the Playwright test using those specific locators.")
        step_num += 1
    else:
        print(f"[Pipeline] Playwright spec already exists. Skipping Browser & Developer initial code write.")

    coordinator_tasks.append(
        f"{step_num}. Feedback Loop (Do this up to {max_iterations} times):\n"
        f"   a. Use `ask_agent_TesterAgent` to run the test {spec_file} and generate the report.\n"
        f"   b. If the TesterAgent replies with PASS, break the loop and move to step {step_num + 1}.\n"
        f"   c. If the TesterAgent replies with FAIL, take the EXACT failure output and send it via `ask_agent_DeveloperAgent` telling them to fix the code. Ensure DeveloperAgent physically overwrites the file."
    )
    step_num += 1

    coordinator_tasks.append(f"{step_num}. Once the test passes (or you exhaust your {max_iterations} attempts), use `ask_agent_CodeReviewerAgent` to write the final review and ensure it incorporates the report feedback.")

    tasks_str = "\n".join(coordinator_tasks)

    # Create the primary Coordinator agent
    coordinator = Agent(
        name="Coordinator",
        verbose=True,
        system_prompt=f"""You are the Test Automation Coordinator. Your job is to orchestrate the multi-agent pipeline for test {test_id}.
You must delegate tasks to your sub-agents in this EXACT order:

{tasks_str}

Do NOT write code, find locators, test code, or review code yourself. ALWAYS use your agent collaboration tools to perform the steps."""
    )

    # Connect the multi-agent network via register_collaborator
    coordinator.register_collaborator(jira_agent, max_iterations=max_iterations)
    coordinator.register_collaborator(browser_agent, max_iterations=max_iterations)
    coordinator.register_collaborator(dev_agent, max_iterations=max_iterations)
    coordinator.register_collaborator(tester_agent, max_iterations=max_iterations)
    coordinator.register_collaborator(reviewer_agent, max_iterations=max_iterations)

    # Launch sequence
    print(f"\n[Pipeline] Launching Coordinator Agent...")
    response = coordinator.run("Execute the 5-step multi-agent automated testing pipeline for this ticket.", max_iterations=max_iterations)
    
    banner("PIPELINE COMPLETE")
    print("--- Final Coordinator Summary ---")
    print(response)
    print()
