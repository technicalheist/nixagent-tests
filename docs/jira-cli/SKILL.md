---
name: jira-cli
description: Interact with Jira from the command line to create, list, view, edit, and transition issues, manage sprints and epics, and perform common Jira workflows. Use when the user asks about Jira tasks, tickets, issues, sprints, or needs to manage project work items.
---

# Jira CLI Skill

Interact with Atlassian Jira from the command line using [jira-cli](https://github.com/ankitpokhrel/jira-cli).

## Prerequisites

- `jira-cli` is installed and the user is **already logged in and configured**. No init, token setup, or authentication steps are required.

## When to Use

- User asks to create, view, edit, or search Jira issues/tickets
- User needs to transition issues through workflow states (To Do → In Progress → Done)
- User wants to manage sprints or epics
- User needs to assign issues or add comments
- User asks about their current tasks or sprint progress

---

## Issue Commands

### List Issues

> Always prefer `--plain` for agent-readable output. Use `--columns` to limit fields.

```bash
# List all issues in current project
jira issue list --plain

# List my assigned issues
jira issue list --plain -a$(jira me)

# Filter by status
jira issue list --plain -s"In Progress"

# Filter by priority
jira issue list --plain -yHigh

# Combined filters
jira issue list --plain -a$(jira me) -s"To Do" -yHigh --created week

# Raw JQL query
jira issue list --plain -q "project = PROJ AND status = 'In Progress' ORDER BY priority DESC"

# Compact output — key, summary, status only (best for agents)
jira issue list --plain --columns key,summary,status --no-headers
```

### View Issue

```bash
# View issue details (plain text — best for agents)
jira issue view ISSUE-123 --plain

# View with comments
jira issue view ISSUE-123 --plain --comments 10
```

### Create Issue

> Always use `--no-input` to skip interactive prompts.

```bash
# Create a bug
jira issue create -tBug -s"Login button not working" -b"Steps to reproduce..." -yHigh --no-input

# Create a story
jira issue create -tStory -s"Add user authentication" -yMedium --no-input

# Create a task
jira issue create -tTask -s"Update dependencies" -lmaintenance --no-input

# Create and assign to self immediately
jira issue create -tBug -s"Fix crash on startup" -a$(jira me) --no-input
```

### Edit Issue

```bash
# Update summary
jira issue edit ISSUE-123 -s"Updated summary" --no-input

# Update description
jira issue edit ISSUE-123 -b"New description" --no-input

# Change priority
jira issue edit ISSUE-123 -yHigh --no-input

# Add a label
jira issue edit ISSUE-123 -lnew-label --no-input
```

### Transition (Move) Issue

```bash
# Move to a new status
jira issue move ISSUE-123 "In Progress"

# Move with a comment
jira issue move ISSUE-123 "Done" --comment "Completed the task"

# Move and set resolution
jira issue move ISSUE-123 "Done" -RFixed
```

### Assign Issue

```bash
# Assign to self
jira issue assign ISSUE-123 $(jira me)

# Assign to a specific user
jira issue assign ISSUE-123 username

# Unassign
jira issue assign ISSUE-123 x
```

### Comment on Issue

```bash
# Add a comment inline
jira issue comment add ISSUE-123 "Investigation complete, fix pushed to branch."
```

### Link & Clone Issues

```bash
# Link two issues
jira issue link ISSUE-123 ISSUE-456 Blocks

# Clone an issue
jira issue clone ISSUE-123 -s"Cloned: New summary"

# Delete an issue
jira issue delete ISSUE-123
```

---

## Epic Commands

```bash
# List epics (plain output)
jira epic list --plain

# Create an epic
jira epic create -n"Q1 Features" -s"Epic summary" -b"Epic description" --no-input

# Add issues to an epic
jira epic add EPIC-1 ISSUE-123 ISSUE-456

# Remove issues from an epic
jira epic remove ISSUE-123 ISSUE-456
```

---

## Sprint Commands

```bash
# List sprints (plain output)
jira sprint list --plain

# View current/active sprint
jira sprint list --plain --current

# View my issues in the current sprint
jira sprint list --plain --current -a$(jira me)

# Add issues to a sprint
jira sprint add SPRINT_ID ISSUE-123 ISSUE-456
```

---

## Project Commands

```bash
# List all projects
jira project list --plain
```

---

## Key Flags Reference

| Flag | Short | Description |
|---|---|---|
| `--plain` | | **Plain text output — use this by default for agents** |
| `--no-input` | | Skip all interactive prompts |
| `--no-headers` | | Omit column headers (useful with `--plain`) |
| `--columns <fields>` | | Limit output columns, e.g. `key,summary,status` |
| `--raw` | | Raw JSON output for structured parsing |
| `--type` | `-t` | Issue type: Bug, Story, Task, Epic |
| `--summary` | `-s` | Issue title/summary |
| `--body` | `-b` | Issue description |
| `--priority` | `-y` | Priority: Highest, High, Medium, Low, Lowest |
| `--label` | `-l` | Label (repeatable: `-lfoo -lbar`) |
| `--assignee` | `-a` | Assignee username |
| `--component` | `-C` | Component name |
| `--parent` | `-P` | Parent issue or epic key |
| `--jql` | `-q` | Raw JQL query string |
| `--created` | | Filter by creation date: `-7d`, `week`, `month` |
| `--order-by` | | Sort field |

---

## Common Workflows

### Start Working on an Issue

```bash
jira issue assign ISSUE-123 $(jira me)
jira issue move ISSUE-123 "In Progress"
```

### Complete an Issue

```bash
jira issue move ISSUE-123 "Done" --comment "Implementation complete." -RFixed
```

### Daily Standup — My Current Sprint Tasks

```bash
jira sprint list --plain --current -a$(jira me)
```

### Create and Assign a Bug in One Flow

```bash
jira issue create -tBug -s"App crashes on login" -yHigh -a$(jira me) --no-input
# Use the returned issue key for next steps
jira issue move BUG-123 "In Progress"
```

### Search Issues with JQL

```bash
# Open high-priority bugs assigned to me, updated this week
jira issue list --plain \
  -q "project = PROJ AND type = Bug AND priority = High AND assignee = currentUser() AND updated >= -7d" \
  --columns key,summary,status --no-headers
```
