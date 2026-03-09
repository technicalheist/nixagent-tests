"""
server.py
─────────
Flask backend for the AI Test Orchestrator UI.
Templates: lib/templates/index.html
Static:    lib/static/css/style.css  |  lib/static/js/app.js

Run:
    .venv\Scripts\python.exe server.py
Then open: http://localhost:5000
"""

import sys
# Fix Windows charmap UnicodeEncodeError before anything else
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import os
import re
import glob
import json
import queue
import signal
import subprocess
import threading
from flask import Flask, Response, jsonify, request, render_template

app = Flask(__name__, 
            static_folder=os.path.join("lib", "static"), 
            template_folder=os.path.join("lib", "templates"))

BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
TESTS_DIR  = os.path.join(BASE_DIR, "tests")
_venv_python = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
PYTHON_EXE = _venv_python if os.path.isfile(_venv_python) else sys.executable

# ─────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    from dotenv import load_dotenv
    load_dotenv()
    
    provider = os.getenv("PROVIDER", "openai").lower()
    if provider == "anthropic":
        model_name = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
    elif provider == "gemini":
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    elif provider == "vertex":
        model_name = os.getenv("VERTEX_MODEL", "gemini-2.5-flash-lite")
    elif provider == "qwen":
        model_name = os.getenv("QWEN_MODEL", "qwen3.5-plus")
    else:
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
        
    return render_template("index.html", active_model=model_name)


@app.route("/api/tests")
def list_tests():
    files = glob.glob(os.path.join(TESTS_DIR, "*.py"))
    tests = [
        {"id": os.path.basename(f).replace(".py", ""), "file": f}
        for f in sorted(files)
    ]
    return jsonify(tests)


@app.route("/api/agents")
def get_agents():
    """
    Collect Agent(name=...) values from the test file AND all library files it
    transitively imports under BASE_DIR/lib.  Order is preserved; duplicates
    are removed.

    Special case: run_all_test — scans every sibling THIN-*.py via BFS and
    appends ConsolidatorAgent (defined inline) at the end.
    """
    test_id   = request.args.get("test", "")
    test_file = os.path.join(TESTS_DIR, f"{test_id}.py")

    if not test_id or not os.path.isfile(test_file):
        return jsonify([])

    LIB_DIR = os.path.join(BASE_DIR, "lib")

    # ── helpers ──────────────────────────────────────────────────────────────

    def _agent_names_in(source: str) -> list:
        """Return all Agent(name=...) values found in *source* text."""
        return re.findall(r'Agent\s*\(\s*name\s*=\s*["\']([^"\']+)["\']', source)

    def _py_file_for_import(module_name: str) -> str | None:
        """
        Try to resolve a bare module name (e.g. 'pipelines.automated_test_generator'
        or 'agents.jira_agent') to an absolute .py path under LIB_DIR.
        Returns None if not found.
        """
        parts  = module_name.replace(".", os.sep)
        # direct file
        direct = os.path.join(LIB_DIR, parts + ".py")
        if os.path.isfile(direct):
            return direct
        # package __init__
        pkg = os.path.join(LIB_DIR, parts, "__init__.py")
        if os.path.isfile(pkg):
            return pkg
        return None

    def _imports_in(source: str) -> list:
        """Extract module names from 'from X import ...' and 'import X' lines."""
        modules = []
        for m in re.finditer(r'^\s*from\s+([\w.]+)\s+import', source, re.MULTILINE):
            modules.append(m.group(1))
        for m in re.finditer(r'^\s*import\s+([\w.,\s]+)', source, re.MULTILINE):
            for part in m.group(1).split(","):
                modules.append(part.strip().split()[0])
        return modules

    # ── BFS helper ───────────────────────────────────────────────────────────

    def _bfs_agents(seed_files: list) -> list:
        """Return ordered, deduplicated agent names reachable from seed_files."""
        visited: set     = set()
        queue:   list    = list(seed_files)
        seen:    set     = set()
        names:   list    = []

        while queue:
            path = queue.pop(0)
            if path in visited:
                continue
            visited.add(path)

            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    src = fh.read()
            except OSError:
                continue

            for name in _agent_names_in(src):
                if name not in seen:
                    seen.add(name)
                    names.append(name)

            for mod in _imports_in(src):
                resolved = _py_file_for_import(mod)
                if resolved and resolved not in visited:
                    queue.append(resolved)

        return names

    # ── Special case: run_all_test ───────────────────────────────────────────
    if test_id == "run_all_test":
        # Seed BFS with every THIN-*.py in the tests folder
        sibling_files = sorted(
            f for f in glob.glob(os.path.join(TESTS_DIR, "*.py"))
            if os.path.basename(f) not in ("run_all_test.py",)
            and not os.path.basename(f).startswith("__")
        )
        agents = _bfs_agents(sibling_files)
        # ConsolidatorAgent lives inline in run_all_test.py — add it explicitly
        if "ConsolidatorAgent" not in agents:
            agents.append("ConsolidatorAgent")
        return jsonify(agents)

    # ── Standard case ────────────────────────────────────────────────────────
    return jsonify(_bfs_agents([test_file]))



@app.route("/api/run")
def run_test():
    test_id   = request.args.get("test", "")
    test_file = os.path.join(TESTS_DIR, f"{test_id}.py")

    if not test_id or not os.path.isfile(test_file):
        return jsonify({"error": "Test not found"}), 404

    # Kill the subprocess if it produces no output for this many seconds.
    IDLE_TIMEOUT = 300  # 5 minutes — adjust as needed

    def generate():
        proc = subprocess.Popen(
            [PYTHON_EXE, "-u", test_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=BASE_DIR,
        )

        line_queue: queue.Queue = queue.Queue()
        _SENTINEL = object()   # signals the reader thread that stdout closed

        def _reader():
            """Push every line from proc.stdout onto the queue, then sentinel."""
            try:
                for line in proc.stdout:
                    line_queue.put(line)
            finally:
                line_queue.put(_SENTINEL)

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()

        try:
            while True:
                try:
                    item = line_queue.get(timeout=IDLE_TIMEOUT)
                except queue.Empty:
                    # No output for IDLE_TIMEOUT seconds — kill the stuck process
                    proc.kill()
                    yield (
                        f"data: {json.dumps({'log': f'[server] Process killed — no output for {IDLE_TIMEOUT}s (hung command)'})}\n\n"
                    )
                    break

                if item is _SENTINEL:
                    break  # stdout closed normally
                yield f"data: {json.dumps({'log': item.rstrip()})}\n\n"
        finally:
            proc.wait()
            yield f"data: {json.dumps({'done': True, 'code': proc.returncode})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/artifact")
def get_artifact():
    test_id = request.args.get("test", "")
    af_type = request.args.get("type", "")

    # ── Special case: run_all_test ───────────────────────────────────────────
    if test_id == "run_all_test":
        if af_type == "consolidated" or af_type == "report":
            # Serve the AI-consolidated report
            path = os.path.join(BASE_DIR, "public", "report", "consolidated_report.md")
            if not os.path.isfile(path):
                return jsonify({"error": "Consolidated report not generated yet"}), 404
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return jsonify({"content": f.read(), "type": af_type})
        elif af_type == "ticket":
            # Build a combined listing of all individual tickets
            ticket_dir = os.path.join(BASE_DIR, "public", "tickets")
            lines = ["# All Tickets\n"]
            for md in sorted(glob.glob(os.path.join(ticket_dir, "THIN-*.md"))):
                tid = os.path.basename(md).replace(".md", "")
                lines.append(f"---\n## {tid}\n")
                with open(md, "r", encoding="utf-8", errors="replace") as f:
                    lines.append(f.read())
            if len(lines) == 1:
                return jsonify({"error": "No individual tickets found yet"}), 404
            return jsonify({"content": "\n".join(lines), "type": "ticket"})
        elif af_type == "review":
            # Build a combined code-review listing
            review_dir = os.path.join(BASE_DIR, "public", "code-review")
            lines = ["# All Code Reviews\n"]
            for md in sorted(glob.glob(os.path.join(review_dir, "THIN-*.md"))):
                tid = os.path.basename(md).replace(".md", "")
                lines.append(f"---\n## {tid}\n")
                with open(md, "r", encoding="utf-8", errors="replace") as f:
                    lines.append(f.read())
            if len(lines) == 1:
                return jsonify({"error": "No individual code reviews found yet"}), 404
            return jsonify({"content": "\n".join(lines), "type": "review"})
        else:  # spec — not applicable for run_all_test
            return jsonify({"error": "No single spec file for run_all_test — see individual tests"}), 404

    # ── Standard case ────────────────────────────────────────────────────────
    paths = {
        "ticket": os.path.join(BASE_DIR, "public", "tickets",           f"{test_id}.md"),
        "spec":   os.path.join(BASE_DIR, "public", "projects", "tests", f"{test_id}.spec.js"),
        "report": os.path.join(BASE_DIR, "public", "report",            f"{test_id}.md"),
        "review": os.path.join(BASE_DIR, "public", "code-review",       f"{test_id}.md"),
    }

    path = paths.get(af_type)
    if not path or not os.path.isfile(path):
        return jsonify({"error": "File not found"}), 404

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    return jsonify({"content": content, "type": af_type})


# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  AI Test Orchestrator UI")
    print("  http://localhost:5000")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
