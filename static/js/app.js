// app.js — AI Test Orchestrator frontend logic

// ── Icon mapping — matched by substring of agent name (lowercase) ──
const ICON_MAP = [
    ['jira', '\uD83C\uDFAB'],   // 🎫
    ['dev', '\uD83D\uDCBB'],   // 💻
    ['code', '\uD83D\uDCBB'],   // 💻
    ['test', '\uD83E\uDDEA'],   // 🧪
    ['qa', '\uD83E\uDDEA'],   // 🧪
    ['review', '\uD83D\uDD0D'],   // 🔍
    ['report', '\uD83D\uDCCA'],   // 📊
    ['browser', '\uD83C\uDF10'],   // 🌐
    ['security', '\uD83D\uDD10'],   // 🔐
    ['deploy', '\uD83D\uDE80'],   // 🚀
    ['data', '\uD83D\uDDC4'],   // 🗄
];

function agentIcon(name) {
    const lower = name.toLowerCase();
    for (const [key, icon] of ICON_MAP) {
        if (lower.includes(key)) return icon;
    }
    return '\uD83E\uDD16'; // 🤖 default
}

function agentDisplayName(name) {
    // "DeveloperAgent" -> "Developer Agent", "JiraAgent" -> "Jira Agent"
    return name.replace(/([a-z])([A-Z])/g, '$1 $2');
}

// ── Theme toggle ────────────────────────────────────────────────
function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.getAttribute('data-theme') === 'dark';
    const next = isDark ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    document.getElementById('themeBtn').textContent = next === 'dark' ? '\uD83C\uDF19' : '\u2600\uFE0F';
    localStorage.setItem('theme', next);
}

// Restore saved theme on load
(function () {
    const saved = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    // Button icon will be set once DOM is ready (DOMContentLoaded)
})();

// ── State ──────────────────────────────────────────────────────
let AGENTS = [];   // populated dynamically per test
let currentTest = '';
let startTime = null;
let timerInterval = null;
let activeAgent = null;
let iterCount = 0;
let eventSource = null;

// ── Bootstrap ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/tests')
        .then(r => r.json())
        .then(tests => {
            const sel = document.getElementById('testSelect');
            sel.innerHTML = '<option value="">— Select a test —</option>';
            tests.forEach(t => {
                const o = document.createElement('option');
                o.value = t.id;
                o.textContent = t.id;
                sel.appendChild(o);
            });

            sel.addEventListener('change', () => {
                const val = sel.value;
                document.getElementById('runBtn').disabled = !val;
                if (val) loadAgents(val);
                else resetAgentList();
            });
        });
});

// ── Load agents for selected test ──────────────────────────────
function loadAgents(testId) {
    fetch(`/api/agents?test=${encodeURIComponent(testId)}`)
        .then(r => r.json())
        .then(names => {
            AGENTS = names;
            renderAgentList(names, 'idle');
        });
}

function renderAgentList(names, state) {
    const list = document.getElementById('agentList');

    if (!names || names.length === 0) {
        list.innerHTML = '<div class="agent-placeholder">No agents found in test file</div>';
        return;
    }

    list.innerHTML = names.map(name => `
    <div class="agent-card" id="card-${name}">
      <div class="agent-icon">${agentIcon(name)}</div>
      <div class="agent-info">
        <div class="agent-name">${agentDisplayName(name)}</div>
        <div class="agent-status" id="status-${name}">Waiting</div>
      </div>
      <div class="agent-dot"></div>
    </div>
  `).join('');
}

function resetAgentList() {
    AGENTS = [];
    document.getElementById('agentList').innerHTML =
        '<div class="agent-placeholder">Select a test to see agents</div>';
}

// ── Timer ───────────────────────────────────────────────────────
function startTimer() {
    startTime = Date.now();
    timerInterval = setInterval(() => {
        const s = Math.floor((Date.now() - startTime) / 1000);
        const m = Math.floor(s / 60);
        const ss = String(s % 60).padStart(2, '0');
        document.getElementById('stat-duration').textContent =
            m > 0 ? `${m}m ${ss}s` : `${s}s`;
    }, 1000);
}
function stopTimer() { clearInterval(timerInterval); }

// ── Agent state ─────────────────────────────────────────────────
function resetAgents() {
    AGENTS.forEach(name => {
        const card = document.getElementById('card-' + name);
        if (card) {
            card.className = 'agent-card';
            document.getElementById('status-' + name).textContent = 'Waiting';
        }
    });
    activeAgent = null;
    iterCount = 0;
    document.getElementById('stat-iter').textContent = '\u2014';
}

function setAgentActive(name, iter) {
    // Mark previous agent as done
    if (activeAgent && activeAgent !== name) {
        const prev = document.getElementById('card-' + activeAgent);
        if (prev && !prev.classList.contains('failed')) {
            prev.className = 'agent-card done';
            document.getElementById('status-' + activeAgent).textContent = 'Done \u2713';
        }
    }
    activeAgent = name;
    const card = document.getElementById('card-' + name);
    if (card) {
        card.className = 'agent-card active';
        document.getElementById('status-' + name).textContent =
            iter ? `Iteration ${iter}` : 'Running\u2026';
    }
}

function markAgentDone(name) {
    const card = document.getElementById('card-' + name);
    if (card && !card.classList.contains('failed')) {
        card.className = 'agent-card done';
        document.getElementById('status-' + name).textContent = 'Done \u2713';
    }
}

function markAllDone() {
    AGENTS.forEach(name => markAgentDone(name));
}

// ── Log panel ───────────────────────────────────────────────────
function clearLog() {
    document.getElementById('logBody').innerHTML =
        '<div class="empty-log"><div class="empty-log-icon">\u26a1</div><p>Log cleared</p></div>';
}

function classifyLine(line) {
    if (!line.trim()) return 'dim';
    if (line.includes('======') || line.includes('PIPELINE COMPLETE')) return 'banner';
    if (line.includes('[Pipeline]') && (line.includes('PASS') || line.includes('done'))) return 'success';
    if (line.includes('\u26a0') || line.includes('WARNING')) return 'warn';
    if (line.includes('ERROR') || line.toLowerCase().includes('traceback')) return 'error';
    if (line.includes('INFO -')) return 'info';
    if (line.includes('Tool Call')) return 'tool';
    if (line.includes('Tool Result')) return 'result';
    if (line.startsWith('  ') || line.includes('\u2500') || line.includes('\u2550')) return 'banner';
    return 'default';
}

function appendLog(line) {
    const body = document.getElementById('logBody');
    const empty = body.querySelector('.empty-log');
    if (empty) empty.remove();

    const div = document.createElement('div');
    div.className = 'log-line ' + classifyLine(line);
    div.textContent = line;
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;

    // Detect agent iteration from any agent name
    const iterMatch = line.match(/\[(\w+)\] Iteration (\d+)/);
    if (iterMatch) {
        const detected = iterMatch[1];
        // Only track if it's one of our known agents
        if (AGENTS.includes(detected)) {
            setAgentActive(detected, iterMatch[2]);
            iterCount++;
            document.getElementById('stat-iter').textContent = iterCount;
        }
    }

    // Detect pipeline "XxxAgent done" lines
    const doneMatch = line.match(/\[Pipeline\] (\w+) done/);
    if (doneMatch && AGENTS.includes(doneMatch[1])) {
        markAgentDone(doneMatch[1]);
    }

    if (line.includes('Tests PASSED') || line.includes('PASSED on iteration')) {
        setStatus('Passed \u2705', 'var(--success)');
    }
}

function setStatus(text, color) {
    const el = document.getElementById('stat-status');
    el.textContent = text;
    el.style.color = color;
}

function setLogDot(color, glow) {
    const dot = document.getElementById('logDot');
    dot.style.background = color;
    dot.style.boxShadow = glow ? `0 0 8px ${color}` : 'none';
}

// ── Run test ────────────────────────────────────────────────────
function runTest() {
    const sel = document.getElementById('testSelect');
    currentTest = sel.value;
    if (!currentTest) return;

    if (eventSource) { eventSource.close(); eventSource = null; }

    resetAgents();
    clearLog();
    document.getElementById('artifactPanel').classList.remove('open');
    document.getElementById('runBtn').disabled = true;
    document.getElementById('runBtnContent').innerHTML =
        '<span class="spinner"></span>&nbsp;Running\u2026';
    setLogDot('var(--primary)', true);
    document.getElementById('stat-test').textContent = currentTest;
    setStatus('Running', 'var(--primary)');
    startTimer();

    appendLog(`\u25b6  Starting pipeline for: ${currentTest}`);
    appendLog('\u2500'.repeat(60));

    eventSource = new EventSource(`/api/run?test=${encodeURIComponent(currentTest)}`);

    eventSource.onmessage = e => {
        const data = JSON.parse(e.data);

        if (data.log !== undefined) appendLog(data.log);

        if (data.done) {
            eventSource.close(); eventSource = null;
            stopTimer();
            markAllDone();

            const ok = data.code === 0;
            setLogDot(ok ? 'var(--success)' : 'var(--error)', true);
            document.getElementById('runBtn').disabled = false;
            document.getElementById('runBtnContent').textContent = '\u25b6 Run Test';

            const statEl = document.getElementById('stat-status');
            if (statEl.textContent === 'Running') {
                setStatus(ok ? 'Done' : 'Failed', ok ? 'var(--success)' : 'var(--error)');
            }

            setTimeout(() => {
                document.getElementById('artifactPanel').classList.add('open');
                showTab('report');
            }, 700);
        }
    };

    eventSource.onerror = () => {
        if (eventSource) { eventSource.close(); eventSource = null; }
        stopTimer();
        document.getElementById('runBtn').disabled = false;
        document.getElementById('runBtnContent').textContent = '\u25b6 Run Test';
        setLogDot('var(--error)', true);
        setStatus('Error', 'var(--error)');
    };
}

// ── Artifact viewer ─────────────────────────────────────────────
function showTab(type) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    const tabEl = document.getElementById('tab-' + type);
    if (tabEl) tabEl.classList.add('active');

    const content = document.getElementById('artifactContent');
    content.innerHTML =
        '<div class="artifact-empty"><span class="spinner"></span>&nbsp;Loading\u2026</div>';

    fetch(`/api/artifact?test=${encodeURIComponent(currentTest)}&type=${type}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                content.innerHTML =
                    `<div class="artifact-empty">\u26a0\ufe0f ${data.error} \u2014 not generated yet</div>`;
                return;
            }
            if (type === 'spec') {
                const pre = document.createElement('pre');
                pre.className = 'code-viewer';
                pre.textContent = data.content;
                content.innerHTML = '';
                content.appendChild(pre);
            } else {
                const div = document.createElement('div');
                div.className = 'md-body';
                div.innerHTML = marked.parse(data.content);
                content.innerHTML = '';
                content.appendChild(div);
            }
        })
        .catch(() => {
            content.innerHTML =
                '<div class="artifact-empty">\u274c Failed to load artifact</div>';
        });
}
