const state = {};
const $ = (id) => document.getElementById(id);

async function loadState() {
  const response = await fetch('/api/state');
  if (response.status === 401) return window.location.replace('/');
  const data = await response.json();
  const pending = data.approvals.filter((item) => item.status === 'pending').length;
  $('approval-count').textContent = pending;
  $('approval-pill').textContent = `${pending} pending`;
  $('document-count').textContent = data.metrics.documents;
  $('server-time').textContent = `Server ${formatTime(data.server_time)}`;
  $('current-date').textContent = formatDate(data.server_time);
  const firstName = data.user.display_name.split(/\s+/)[0] || data.user.username;
  const hour = new Date(data.server_time).getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  $('welcome-heading').textContent = `${greeting}, ${firstName}`;
  $('session-user').textContent = `Verified for ${data.user.display_name}`;
  $('mfa-status').textContent = data.user.mfa ? 'Verified for this session' : 'Verification required';
  $('documents').innerHTML = data.documents.map((doc) =>
    `<div class="document"><span class="doc-icon">▣</span><div><strong>${doc.name}</strong><small>Updated ${formatTime(doc.updated_at)}</small></div><span class="classification">${doc.classification}</span><button class="ghost document-action" data-resource="${doc.name}">Open</button></div>`).join('');
  document.querySelectorAll('.document-action').forEach((button) => {
    button.addEventListener('click', () => openDocument(button.dataset.resource));
  });
  $('approvals').innerHTML = data.approvals.map((item) =>
    `<div class="approval"><span class="doc-icon">↗</span><div><strong>${item.requester}</strong><small>Access to ${item.resource}</small></div><span class="pill ${item.status === 'pending' ? 'warning' : ''}">${item.status}</span></div>`).join('');
  $('activity').innerHTML = data.activity.map((item) =>
    `<div class="notification"><span class="activity-time">${formatTime(item.timestamp)}</span><div><strong>${item.title}</strong><small>${item.detail}</small></div></div>`).join('');
  $('external-messages').innerHTML = data.external_messages.length
    ? data.external_messages.map((item) =>
      `<div class="notification"><span class="activity-time">${formatTime(item.timestamp)}</span><div><strong>${item.integration}</strong><small>${item.message} · ${item.username}</small></div></div>`).join('')
    : '<p class="muted">No external messages received.</p>';
}

async function loadScenarios() {
  const [availableResponse, runningResponse] = await Promise.all([
    fetch('/api/scenarios/available'),
    fetch('/api/scenarios/running'),
  ]);
  if (availableResponse.status === 401 || runningResponse.status === 401) {
    showLogin();
    return;
  }
  const playbooks = await availableResponse.json();
  const running = await runningResponse.json();
  $('playbook-list').innerHTML = playbooks.map((playbook) =>
    `<article class="playbook-card"><h3>${playbook.name}</h3><p>${playbook.description}</p><div class="playbook-meta"><span>${playbook.event_count} events</span><span>${playbook.mitre_tactics.join(', ')}</span></div><div class="techniques">${playbook.mitre_techniques.map((technique) => `<span>${technique}</span>`).join('')}</div><button class="primary start-scenario" data-filename="${playbook.filename}">▶ Start</button></article>`).join('');
  document.querySelectorAll('.start-scenario').forEach((button) => {
    button.addEventListener('click', () => startScenario(button.dataset.filename));
  });
  $('running-scenarios').classList.toggle('hidden', running.length === 0);
  $('running-list').innerHTML = running.map((run) => renderRunningScenario(run)).join('');
  document.querySelectorAll('[data-scenario-control]').forEach((button) => {
    button.addEventListener('click', () => controlScenario(button.dataset.runId, button.dataset.scenarioControl));
  });
  document.querySelectorAll('[data-scenario-speed]').forEach((select) => {
    select.addEventListener('change', () => controlScenario(select.dataset.runId, 'speed', { speed: Number(select.value) }));
  });
}

function renderRunningScenario(run) {
  const active = run.status === 'running' || run.status === 'paused';
  return `<article class="running-card"><div class="running-header"><strong>${run.scenario_name}</strong><span class="pill">${run.status}</span></div><div class="running-meta"><span>${run.events_generated} events</span><span>${run.speed}x speed</span><span>${formatTime(run.started_at)}</span></div>${active ? `<div class="scenario-controls"><button class="ghost" data-run-id="${run.id}" data-scenario-control="${run.status === 'paused' ? 'resume' : 'pause'}">${run.status === 'paused' ? '▶ Resume' : 'Ⅱ Pause'}</button><button class="ghost" data-run-id="${run.id}" data-scenario-control="stop">■ Stop</button><select data-run-id="${run.id}" data-scenario-speed><option ${run.speed === 0.5 ? 'selected' : ''}>0.5</option><option ${run.speed === 1 ? 'selected' : ''}>1</option><option ${run.speed === 2 ? 'selected' : ''}>2</option><option ${run.speed === 5 ? 'selected' : ''}>5</option></select></div>` : ''}${run.error_message ? `<p class="scenario-error">${run.error_message}</p>` : ''}</article>`;
}

async function startScenario(filename) {
  await scenarioRequest('/api/scenarios/start', 'POST', { filename });
  await loadScenarios();
}

async function controlScenario(runId, action, payload = {}) {
  const method = action === 'speed' ? 'PUT' : 'POST';
  await scenarioRequest(`/api/scenarios/${runId}/${action}`, method, payload);
  await loadScenarios();
}

async function scenarioRequest(url, method, body) {
  const response = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: method === 'POST' || method === 'PUT' ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const data = await response.json();
    const result = $('scenario-result');
    result.textContent = data.message || data.error || 'Scenario operation failed';
    result.classList.remove('hidden');
  }
}

function formatTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Unknown time' : date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Unknown date' : date.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
}

function openDocument(resource) {
  $('modal-file').textContent = resource;
  $('document-modal').classList.remove('hidden');
  $('modal-download').onclick = () => {
    $('document-modal').classList.add('hidden');
    action('download_document', 'scenario-result', resource);
  };
}

async function action(action, resultId = 'scenario-result', resource = 'Customer Export.csv') {
  const response = await fetch('/api/actions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, resource }),
  });
  const data = await response.json();
  if (response.status === 401) return showLogin();
  const result = $(resultId);
  result.textContent = response.ok ? `${data.message} ${data.event_ids.length} SIEM event${data.event_ids.length === 1 ? '' : 's'} recorded. Alerts will appear after correlation completes.` : data.error;
  result.classList.remove('hidden');
  await loadState();
}

$('approve').addEventListener('click', () => action('approve_request'));
$('reject').addEventListener('click', () => action('reject_request'));
$('logout').addEventListener('click', async () => {
  await fetch('/api/logout', { method: 'POST' });
  window.location.replace('/');
});
$('close-modal').addEventListener('click', () => $('document-modal').classList.add('hidden'));
$('document-modal').addEventListener('click', (event) => {
  if (event.target === $('document-modal')) $('document-modal').classList.add('hidden');
});

async function checkSession() {
  const response = await fetch('/api/session');
  const data = await response.json();
  if (!data.authenticated) return window.location.replace('/');
  await loadState();
}

checkSession();
