"""
browser_use.py — Tool for LLM agents to control the browser-use CLI.

All commands run in the *same* persistent browser session that browser-use
keeps alive between calls.

Auto-state behaviour
────────────────────
Every command that mutates the page (open, click, input, type, keys, scroll,
back) automatically fetches and appends `browser-use state` to its output.
The LLM therefore NEVER needs to call `state` explicitly — it always has the
current element list in the response of the previous action.

Quick reference (from browser_use_cheatsheet.md):
  open <url>          → navigate to URL          [state auto-appended]
  back                → go back                  [state auto-appended]
  scroll down/up      → scroll the page          [state auto-appended]
  state               → get current URL, title, and clickable element list
  click <index>       → click element at <index> [state auto-appended]
  input <index> "txt" → click+type (preferred)   [state auto-appended]
  type "text"         → type into focused element [state auto-appended]
  keys "Enter"        → send a keyboard key      [state auto-appended]
  get text <index>    → extract text of element at <index>
  get html            → full page HTML
  get html --selector "css" → HTML of a specific element
  get title           → current page title
  close --all         → close all browser sessions (run when task is finished)
"""

import subprocess
from typing import Optional


# ---------------------------------------------------------------------------
# Low-level runner
# ---------------------------------------------------------------------------

def _run(args: list[str], timeout: int = 30) -> str:
    """
    Execute `browser-use <args>` and return its stdout+stderr as a string.

    Raises RuntimeError if the command exits with a non-zero code.
    """
    cmd = ["browser-use"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            raise RuntimeError(
                f"browser-use failed (exit {result.returncode}):\n{output}"
            )
        return output
    except FileNotFoundError:
        raise RuntimeError(
            "browser-use CLI not found. "
            "Make sure it is installed and available on PATH."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"browser-use command timed out after {timeout}s: {' '.join(cmd)}"
        )


# ---------------------------------------------------------------------------
# High-level tool functions (call these from your agent / tool-caller)
# ---------------------------------------------------------------------------

# Commands that mutate the page — state is auto-appended after each of these.
_MUTATING_CMDS = {"open", "click", "input", "type", "keys", "scroll", "back"}


def browser_use(command: str, headed: bool = False) -> str:
    """
    Execute any browser-use CLI command and return the output.

    Auto-state behaviour
    --------------------
    After any command that changes the page (open, click, input, type, keys,
    scroll, back), `browser-use state` is fetched automatically and appended
    to the response. The LLM therefore always has the current element list
    after every action — no explicit `state` call is ever needed.

    Parameters
    ----------
    command : str
        The browser-use sub-command string, e.g. ``"open https://example.com"``
        or ``"click 3"`` or ``"input 5 \\"search term\\""``.
    headed : bool
        If True, adds ``--headed`` flag so you can watch the browser window
        (only meaningful for the ``open`` command).

    Returns
    -------
    str
        The CLI output. For mutating commands, the current page state is
        automatically appended so no follow-up `state` call is needed.

    Examples
    --------
    >>> output = browser_use("open https://news.ycombinator.com")
    >>> # output already contains page state — no need to call state again

    >>> output = browser_use("click 2")
    >>> # output already contains updated page state after the click

    >>> output = browser_use('input 4 "hello world"')
    >>> output = browser_use('keys "Enter"')
    >>> output = browser_use("get text 1")   # read-only — no auto-state
    >>> output = browser_use("close --all")  # cleanup — no auto-state
    """
    parts = command.strip().split(maxsplit=1)
    sub_cmd = parts[0].lower() if parts else ""

    # Build argument list
    args: list[str] = []
    if headed and sub_cmd == "open":
        args.append("--headed")
    args += command.strip().split()

    # Run the primary command
    output = _run(args)

    # Auto-append state after every mutating command so the LLM always has
    # fresh element indexes without needing a separate state call.
    if sub_cmd in _MUTATING_CMDS:
        label = f"browser-use: after '{sub_cmd}' — current state (auto-fetched)"
        try:
            state_output = _run(["state"])
            output = f"{output}\n\n[{label}]\n{state_output}"
        except RuntimeError as exc:
            output += f"\n\n[browser-use: state fetch failed — {exc}]"

    return output


# ---------------------------------------------------------------------------
# Convenience wrappers (optional — makes tool-call schemas cleaner)
# ---------------------------------------------------------------------------

def browser_open(url: str, headed: bool = False) -> str:
    """Open a URL and return the page state immediately."""
    return browser_use(f"open {url}", headed=headed)


def browser_state() -> str:
    """Return the current browser page state (URL, title, elements)."""
    return _run(["state"])


def browser_click(index: int) -> str:
    """Click the element at the given index."""
    return browser_use(f"click {index}")


def browser_input(index: int, text: str) -> str:
    """Click element at index and type text into it (recommended approach)."""
    return browser_use(f'input {index} "{text}"')


def browser_type(text: str) -> str:
    """Type text into the currently focused element."""
    return browser_use(f'type "{text}"')


def browser_keys(key: str) -> str:
    """Send a keyboard key, e.g. 'Enter', 'Tab', 'Escape'."""
    return browser_use(f'keys "{key}"')


def browser_scroll(direction: str = "down") -> str:
    """Scroll the page up or down."""
    assert direction in ("up", "down"), "direction must be 'up' or 'down'"
    return browser_use(f"scroll {direction}")


def browser_back() -> str:
    """Navigate back."""
    return browser_use("back")


def browser_get_text(index: int) -> str:
    """Get the text content of the element at index."""
    return browser_use(f"get text {index}")


def browser_get_html(selector: Optional[str] = None) -> str:
    """Get full page HTML, or HTML of a specific CSS selector."""
    if selector:
        return browser_use(f'get html --selector "{selector}"')
    return browser_use("get html")


def browser_get_title() -> str:
    """Get the current page title."""
    return browser_use("get title")


def browser_close() -> str:
    """Close all browser sessions. Call this when the task is finished."""
    return browser_use("close --all")


# ---------------------------------------------------------------------------
# LLM tool schema (OpenAI-compatible function definition)
# ---------------------------------------------------------------------------

BROWSER_USE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "browser_use",
        "description": (
            "Execute a browser-use CLI command to control a persistent browser "
            "session. "
            "IMPORTANT: After any command that changes the page (open, click, "
            "input, type, keys, scroll, back), the current page state is "
            "returned automatically in the response — you NEVER need to call "
            "'state' separately. Just act on the state already in the response. "
            "Finish every browser task with 'close --all'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "The browser-use sub-command to run. Examples:\n"
                        "  'open https://example.com'  → navigates, returns state\n"
                        "  'click 3'                   → clicks, returns updated state\n"
                        "  'input 5 \"search query\"'   → click+type, returns updated state\n"
                        "  'type \"hello\"'             → types, returns updated state\n"
                        "  'keys \"Enter\"'             → key press, returns updated state\n"
                        "  'scroll down'               → scrolls, returns updated state\n"
                        "  'scroll up'                 → scrolls, returns updated state\n"
                        "  'back'                      → navigates back, returns updated state\n"
                        "  'state'                     → explicit state fetch (rarely needed)\n"
                        "  'get text 2'                → returns element text only\n"
                        "  'get html'                  → returns full page HTML\n"
                        "  'get html --selector \"h1\"' → returns scoped HTML\n"
                        "  'get title'                 → returns page title\n"
                        "  'close --all'               → closes all sessions"
                    ),
                },
                "headed": {
                    "type": "boolean",
                    "description": (
                        "If true, opens the browser in headed (visible) mode. "
                        "Only applies to the 'open' command. Defaults to false."
                    ),
                },
            },
            "required": ["command"],
        },
    },
}
