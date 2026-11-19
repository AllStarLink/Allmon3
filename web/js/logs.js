/* Metadata-only log viewer. No AMI commands or radio actions. */
let logState = null;
let logRows = [];
let logsActive = false;
let logsEpoch = 0;
let logsReadID = 0;
let logsBusy = false;
let logsMutation = false;
const logEl = id => document.getElementById(id);

function logMessage(message, error = false) {
    const el = logEl('logs-feedback');
    el.textContent = message;
    el.className = message ? 'alert ' + (error ? 'alert-danger' : 'alert-info') : '';
}
async function logRequest(path, options = {}) {
    const response = await fetch('master/logs/' + path, {cache: 'no-store', ...options});
    const text = await response.text();
    let result;
    try { result = JSON.parse(text); } catch (_) { result = {}; }
    if (!response.ok || !Object.hasOwn(result, 'SUCCESS')) {
        throw new Error(result.ERROR || result.SECURITY || (response.status === 403 ? 'Log in with permission to view this log.' : 'Unable to load logs (' + response.status + ').'));
    }
    return result.SUCCESS;
}
function clearLogRows(message = '') {
    logRows = [];
    logEl('logs-output').textContent = message;
    logEl('logs-read-status').textContent = '';
    logEl('logs-download').disabled = true;
}
async function logsAuthChanged() {
    if (!logEl('logs-manager')) return;
    if (!loggedIn) {
        logsActive = false; logState = null; logsEpoch++; logsReadID++;
        logEl('logs-auto').checked = false;
        logEl('logs-manager').open = false;
        logEl('logs-manager').classList.add('d-none');
        logEl('logs-navigation').classList.add('d-none');
        logEl('logs-node-controls').replaceChildren();
        logEl('logs-node-controls').dataset.signature = '';
        logEl('logs-node').replaceChildren();
        clearLogRows(); logMessage('');
        return;
    }
    if (logsActive) return;
    logsActive = true;
    const epoch = ++logsEpoch;
    logEl('logs-manager').classList.remove('d-none');
    logEl('logs-navigation').classList.remove('d-none');
    try { await refreshLogSettings(epoch); }
    catch (e) { if (epoch === logsEpoch) logMessage(e.message, true); }
}
function renderLogSettings() {
    const nodeSelect = logEl('logs-node');
    const previous = nodeSelect.value;
    nodeSelect.replaceChildren(...logState.nodes.map(row => new Option(row.node, row.node)));
    if (logState.nodes.some(row => row.node === previous)) nodeSelect.value = previous;
    const controls = logEl('logs-node-controls');
    const signature = JSON.stringify(logState.nodes);
    if (controls.dataset.signature !== signature) {
        controls.dataset.signature = signature;
        controls.replaceChildren();
        for (const row of logState.nodes) {
            const wrap = document.createElement('div'); wrap.className = 'form-check form-switch';
            const input = document.createElement('input');
            input.type = 'checkbox'; input.setAttribute('role', 'switch');
            input.className = 'form-check-input'; input.id = 'logs-enable-' + row.node;
            input.checked = row.enabled; input.disabled = logsMutation;
            input.addEventListener('change', () => toggleConnectionLogging(row.node, input.checked));
            const label = document.createElement('label'); label.className = 'form-check-label';
            label.htmlFor = input.id; label.textContent = row.node + ' — ' + (row.enabled ? 'Recording on' : 'Recording off');
            wrap.append(input, label); controls.append(wrap);
        }
        if (!logState.nodes.length) controls.textContent = 'No connection hooks are configured for your permitted local nodes.';
    }
    const messages = logEl('logs-kind').querySelector('[value="messages"]');
    messages.disabled = !logState.messages_allowed;
    if (!logState.messages_allowed && logEl('logs-kind').value === 'messages') logEl('logs-kind').value = 'connections';
    updateLogScope();
}
async function refreshLogSettings(epoch = logsEpoch) {
    const state = await logRequest('state');
    if (epoch !== logsEpoch || !loggedIn) return;
    logState = state; renderLogSettings();
}
function updateLogScope() {
    const shared = logEl('logs-kind').value === 'messages';
    logEl('logs-node').disabled = shared;
    logEl('logs-scope').textContent = shared
        ? '/var/log/asterisk/messages.log — shared host diagnostics, not a complete per-node history.'
        : '/var/log/asterisk/connectlog — entries for the selected local node only.';
}
async function toggleConnectionLogging(node, enabled) {
    if (logsMutation) return;
    logsMutation = true;
    const epoch = logsEpoch;
    logEl('logs-node-controls').querySelectorAll('input').forEach(el => { el.disabled = true; });
    try {
        await logRequest('nodes/' + encodeURIComponent(node), {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({enabled})
        });
        if (epoch === logsEpoch && loggedIn) logMessage('Connection recording ' + (enabled ? 'enabled' : 'disabled') + ' for ' + node + '. Existing history is unchanged.');
    } catch (e) { if (epoch === logsEpoch) logMessage(e.message, true); }
    finally {
        logsMutation = false;
        if (epoch === logsEpoch && loggedIn) {
            // Re-read persisted truth even on failure; never leave an optimistic switch.
            logEl('logs-node-controls').dataset.signature = '';
            try { await refreshLogSettings(epoch); }
            catch (e) {
                logMessage(e.message, true);
                logEl('logs-node-controls').querySelectorAll('input').forEach(el => { el.disabled = true; });
            }
        }
    }
}
function filteredLogRows() {
    const term = logEl('logs-search').value.toLowerCase();
    return logRows.filter(line => line.toLowerCase().includes(term));
}
function renderLogRows() {
    const rows = filteredLogRows();
    logEl('logs-output').textContent = rows.join('\n') || (logRows.length ? 'No displayed lines match your search.' : 'No entries in this recent log window.');
    logEl('logs-download').disabled = rows.length === 0;
}
async function refreshLogs() {
    if (!loggedIn || logsBusy || !logEl('logs-manager').open) return;
    logsBusy = true;
    const epoch = logsEpoch;
    const readID = ++logsReadID;
    const selection = [logEl('logs-kind').value, logEl('logs-node').value, logEl('logs-limit').value].join('|');
    try {
        if (!logsMutation) await refreshLogSettings(epoch);
        if (epoch !== logsEpoch || !loggedIn) return;
        const kind = logEl('logs-kind').value;
        const node = logEl('logs-node').value;
        if (kind === 'connections' && !node) { clearLogRows('No connection logs available for your nodes.'); return; }
        const result = await logRequest(kind + '?' + new URLSearchParams({node, limit: logEl('logs-limit').value}));
        if (epoch !== logsEpoch || readID !== logsReadID || !loggedIn || selection !== [logEl('logs-kind').value, logEl('logs-node').value, logEl('logs-limit').value].join('|')) return;
        logRows = result.lines;
        renderLogRows();
        logEl('logs-read-status').textContent = (!result.exists ? 'Log file has not been created yet. ' : '') +
            logRows.length + ' lines loaded · refreshed ' + new Date().toLocaleTimeString() + (result.truncated ? ' · older lines omitted' : '');
    } catch (e) {
        if (epoch === logsEpoch && readID === logsReadID) { clearLogRows('Log unavailable.'); logMessage(e.message, true); }
    } finally {
        logsBusy = false;
        if (epoch === logsEpoch && loggedIn && selection !== [logEl('logs-kind').value, logEl('logs-node').value, logEl('logs-limit').value].join('|')) refreshLogs();
    }
}
function openLogsPanel() {
    logEl('logs-manager').open = true;
    logEl('logs-manager').scrollIntoView({block: 'start'});
    logEl('logs-title').focus();
    // Close the collapsed mobile menu just as a navigation action should.
    const sidebar = logEl('sidebarMenu');
    if (window.innerWidth < 768 && sidebar.classList.contains('show')) bootstrap.Collapse.getOrCreateInstance(sidebar).hide();
}
function changeLogSelection() {
    logsReadID++; clearLogRows('Loading…'); updateLogScope(); refreshLogs();
}
logEl('logs-manager').addEventListener('toggle', () => {
    if (logEl('logs-manager').open) refreshLogs();
});
for (const id of ['logs-kind', 'logs-node', 'logs-limit']) logEl(id).addEventListener('change', changeLogSelection);
logEl('logs-refresh').addEventListener('click', refreshLogs);
logEl('logs-search').addEventListener('input', renderLogRows);
logEl('logs-auto').addEventListener('change', () => { if (logEl('logs-auto').checked) refreshLogs(); });
logEl('logs-download').addEventListener('click', () => {
    const blob = new Blob([filteredLogRows().join('\n') + '\n'], {type: 'text/plain;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = url;
    link.download = logEl('logs-kind').value + (logEl('logs-kind').value === 'connections' ? '-' + logEl('logs-node').value : '') + '.txt';
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
setInterval(() => {
    if (loggedIn && !document.hidden && logEl('logs-manager').open && logEl('logs-auto').checked) refreshLogs();
}, 5000);
