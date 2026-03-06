from config import get_test_paths
from helpers.utils import banner, section
from agents.jira_agent import make_jira_agent
from agents.developer_agent import make_developer_agent
from agents.tester_agent import make_tester_agent
from agents.reviewer_agent import make_code_reviewer_agent

def automatedTestGenerator(test_id: str, max_iterations: int = 5):
    """
    Automated Test Generator Pipeline.
    Runs the multi-agent pipeline to automatically fetch tickets, write tests, execute them, and review code.
    """
    paths = get_test_paths(test_id)
    ticket_file = paths["ticket_file"]
    report_file = paths["report_file"]
    review_file = paths["review_file"]
    spec_file = paths["spec_file"]

    banner(f"Automated Test Generator Pipeline | Ticket: {test_id}")
    print(f"  Ticket file : {ticket_file}")
    print(f"  Spec file   : {spec_file}")
    print(f"  Report file : {report_file}")
    print(f"  Review file : {review_file}")

    # ── STEP 1: JiraAgent ────────────────────────────────────────────────────
    section("STEP 1 — JiraAgent: fetch Jira ticket")
    jira_agent = make_jira_agent(test_id, ticket_file)
    jira_result = jira_agent.run(
        f"Fetch and save Jira ticket {test_id} following your instructions."
    )
    print("\n[Pipeline] JiraAgent done.")

    # ── STEP 2: DeveloperAgent (initial code write) ──────────────────────────
    section("STEP 2 — DeveloperAgent: discover locators & write Playwright test")
    dev_agent = make_developer_agent(test_id, ticket_file, spec_file)
    dev_agent.run(
        f"The Jira ticket for {test_id} has been fetched.\n"
        f"JiraAgent summary:\n{jira_result}\n\n"
        f"Follow your instructions: check for existing code, then write the test."
    )
    print("\n[Pipeline] DeveloperAgent done with initial pass.")

    # ── STEP 3: Dev / Test iteration loop ────────────────────────────────────
    test_passed = False
    for iteration in range(1, max_iterations + 1):
        section(f"STEP 3 — TesterAgent (iteration {iteration}/{max_iterations})")

        tester_agent = make_tester_agent(test_id, report_file)
        tester_result = tester_agent.run(
            f"Run the Playwright test for {test_id} following your instructions."
        )

        if "PASS" in tester_result and "FAIL" not in tester_result.upper()[:20]:
            print(f"\n[Pipeline] ✅ Tests PASSED on iteration {iteration}!")
            test_passed = True
            break

        if iteration == max_iterations:
            print(f"\n[Pipeline] ⚠️  Reached max iterations ({max_iterations}) without PASS.")
            break

        # Feed failure details back into the developer's existing conversation
        section(f"STEP 3 — DeveloperAgent fixing failures (iteration {iteration})")
        dev_agent.run(
            f"The TesterAgent ran your Playwright test and it FAILED.\n\n"
            f"Failure details:\n{tester_result}\n\n"
            f"Fix the test at {spec_file} based on the feedback above. "
            f"Do NOT explain — just apply the fix and print CODE_WRITTEN when done."
        )

    # ── STEP 4: CodeReviewerAgent ─────────────────────────────────────────────
    section("STEP 4 — CodeReviewerAgent: final code review")
    reviewer_agent = make_code_reviewer_agent(test_id, review_file)
    reviewer_agent.run(
        f"The Playwright test for {test_id} has been written"
        f"{' and tests passed' if test_passed else ' (tests may have failed)'}. "
        f"Follow your instructions to review the code."
    )
    print("\n[Pipeline] CodeReviewerAgent done.")

    # ── DONE ──────────────────────────────────────────────────────────────────
    banner("PIPELINE COMPLETE")
    print(f"  Ticket   → {ticket_file}")
    print(f"  Spec     → {spec_file}")
    print(f"  Report   → {report_file}")
    print(f"  Review   → {review_file}")
    print()
