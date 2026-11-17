const $ = (id) => document.getElementById(id);

function formatTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Unknown time' : date.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

async function request(url, options = {}) {
  const response = await fetch(url, options);
  if (response.status === 401) {
    window.location.replace('/');
    return null;
  }
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || data.error || 'Scenario operation failed');
  }
  return data;
}

function renderRunning(run) {
  const active = run.status === 'running' || run.status === 'paused';
  return `<article class="running-card"><div class="running-header"><strong>${run.scenario_name}</strong><span class="pill">${run.status}</span></div><div class="running-meta"><span>${run.events_generated} events</span><span>${run.speed}x speed</span><span>${formatTime(run.started_at)}</span></div>${active ? `<div class="scenario-controls"><button class="ghost" data-action="${run.status === 'paused' ? 'resume' : 'pause'}" data-id="${run.id}">${run.status === 'paused' ? '▶ Resume' : 'Ⅱ Pause'}</button><button class="ghost" data-action="stop" data-id="${run.id}">■ Stop</button><select data-action="speed" data-id="${run.id}"><option ${run.speed === 0.5 ? 'selected' : ''}>0.5</option><option ${run.speed === 1 ? 'selected' : ''}>1</option><option ${run.speed === 2 ? 'selected' : ''}>2</option><option ${run.speed === 5 ? 'selected' : ''}>5</option></select></div>` : ''}${run.error_message ? `<p class="scenario-error">${run.error_message}</p>` : ''}</article>`;
}

async function loadScenarios() {
  try {
    const [playbooks, running] = await Promise.all([
      request('/api/scenarios/available'),
      request('/api/scenarios/running'),
    ]);
    if (!playbooks || !running) return;
    $('playbook-list').innerHTML = playbooks.map((playbook) =>
      `<article class="playbook-card"><h3>${playbook.name}</h3><p>${playbook.description}</p><div class="playbook-meta"><span>${playbook.event_count} events</span><span>${playbook.mitre_tactics.join(', ')}</span></div><div class="techniques">${playbook.mitre_techniques.map((technique) => `<span>${technique}</span>`).join('')}</div><button class="primary start-scenario" data-filename="${playbook.filename}">▶ Start</button></article>`).join('');
    $('running-scenarios').classList.toggle('hidden', running.length === 0);
    $('running-list').innerHTML = running.map(renderRunning).join('');
    document.querySelectorAll('.start-scenario').forEach((button) => {
      button.addEventListener('click', () => startScenario(button.dataset.filename));
    });
    document.querySelectorAll('[data-action]').forEach((control) => {
      control.addEventListener('change', () => controlScenario(control));
      control.addEventListener('click', () => controlScenario(control));
    });
  } catch (error) {
    $('scenario-result').textContent = error.message;
    $('scenario-result').classList.remove('hidden');
  }
}

async function startScenario(filename) {
  await request('/api/scenarios/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  });
  await loadScenarios();
}

async function controlScenario(control) {
  const action = control.dataset.action;
  const method = action === 'speed' ? 'PUT' : 'POST';
  const body = action === 'speed' ? { speed: Number(control.value) } : undefined;
  await request(`/api/scenarios/${control.dataset.id}/${action}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  await loadScenarios();
}

$('logout').addEventListener('click', async () => {
  await fetch('/api/logout', { method: 'POST' });
  window.location.replace('/');
});

request('/api/session').then((data) => {
  if (data?.authenticated) loadScenarios();
});
