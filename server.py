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
    return render_template("index.html")


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

    # ── BFS over reachable lib files ─────────────────────────────────────────

    visited: set  = set()
    queue:   list = [test_file]
    seen_names: set  = set()
    unique:     list = []

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

        # Collect agent names from this file
        for name in _agent_names_in(src):
            if name not in seen_names:
                seen_names.add(name)
                unique.append(name)

        # Enqueue reachable lib files (only if they live under LIB_DIR)
        for mod in _imports_in(src):
            resolved = _py_file_for_import(mod)
            if resolved and resolved not in visited:
                queue.append(resolved)

    return jsonify(unique)



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
