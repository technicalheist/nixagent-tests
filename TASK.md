# Multi-Agent Web Testing Automation Task

## Project Overview

This project leverages a multi-agent Python architecture powered by `nixagent` to fully automate the web testing lifecycle. The system divides the workload across four specialized agents—JiraAgent, DeveloperAgent, TesterAgent, and CodeReviewerAgent—to seamlessly transition from reading a Jira ticket to executing, reporting, and reviewing automated browser tests.

## Core Directives for All Agents

* **Time and Resource Efficiency**: Time is our most precious resource. Every agent **MUST** prioritize speed and avoid duplicate work.
* **Artifact Reuse**: Before starting any task, verify if the corresponding file (ticket, test code, report, or review) already exists for the given ID. If it does, skip the execution step, use the existing file, and immediately delegate to the next agent.
* **Ticket ID Tracking**: The system tracks task progress using the ticket ID (e.g., `TEST001`). All artifacts (Jira ticket markdown, test files, reports, code reviews) **MUST** incorporate this `<TEST_ID>` in their filenames.

---

## Agent Roles and Workflows

### 1. JiraAgent

**Objective**: Fetch the Jira ticket documentation and prepare it for downstream development.

**Workflow Instructions**:

1. **Check for Existing Data**: First, check if the ticket file already exists at `public/tickets/<TEST_ID>.md`.
   * *Critical Optimization*: If the file already exists, **SKIP ALL TASKS** and immediately delegate to the DeveloperAgent. Do not spend time invoking any tools or APIs.
2. If the file does not exist, read the Jira CLI documentation located at `docs/jira-cli`. (Assume Jira is already configured on the system).
3. Fetch the requested Jira ticket using the Jira CLI.
4. Save the fetched ticket content to a markdown file inside the `public/tickets/` directory, naming it precisely with the ticket ID (e.g., `public/tickets/TEST001.md`).
5. Delegate the task to the DeveloperAgent.

### 2. DeveloperAgent

**Objective**: Write the exact automation test script based on the Jira ticket using Playwright node js and the local `agent-browser`.

**Workflow Instructions**:

1. **Check for Existing Data**: Check if test code for the ticket already exists in `public/projects/tests/` (prefixed or named with `<TEST_ID>`).
   * *Critical Optimization*: If the test code already exists, **DO NOT REWRITE THE CODE**. Instead, simply run the existing test. If it works, immediately delegate the task to the TesterAgent.
2. If the code does not exist, read the `agent-browser` documentation located at `D:\Projects\Agents\nixagent-tests\docs\agent-browser\SKILL.md`.
3. Use the `agent-browser` to dynamically browse the target pages.
4. Communicate precisely with the browser for each step to extract exact element locators.
5. Write the Playwright test code step-by-step.
6. Once the code is complete, run the tests locally.
7. If the test passes, delegate the task to the TesterAgent.
8. If the TesterAgent flags a failure later on, rectify the code and repeat the testing process.

**Strict Constraints for DeveloperAgent**:

* **No Documentation**: Your job is *strictly* to run the browser, get locators, write the code, and test it. **DO NOT** generate any supplementary documentation, and **DO NOT** write a `README` file. This agent must operate at maximum speed.
* **Playwright Configurations**: The Playwright setup is already configured globally. **DO NOT TOUCH** the `public/projects/playwright.config.js` file.
* **Test Location**: All test scripts **MUST** strictly be written inside the `public/projects/tests/` folder.

### 3. TesterAgent

**Objective**: Validate the test code's reliability and generate completion reports.

**Workflow Instructions**:

1. **Check for Existing Data**: Verify if a detailed test report already exists for `<TEST_ID>` in the `public/report/` folder. If it does, skip execution and delegate to the CodeReviewerAgent.
2. Run the tests located in `public/projects/tests/` corresponding to the provided `<TEST_ID>`.
   * *If the test fails*: Send the precise issue, logs, and failure states back to the DeveloperAgent for immediate rectification. This loop must continue until the tests pass.
   * *If the test passes*: Generate a detailed test report and save it inside the `public/report/` folder.
3. Once the report is finalized, delegate the completion status to the CodeReviewerAgent.

### 4. CodeReviewerAgent

**Objective**: Perform a robust final review of the successful testing code.

**Workflow Instructions**:

1. **Check for Existing Data**: Check if a code review document already exists for this `<TEST_ID>` in the `public/code-review/` folder. If yes, the overall workflow is complete.
2. If no review exists, systematically analyze the provided test code.
3. Create a dedicated, insightful code review document.
4. Save the review document inside the `public/code-review/` folder.
