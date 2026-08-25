'use strict';

const CAPACITIES = [
  {value: 0.05, label: '5%', count: '7 tasks'},
  {value: 0.1, label: '10%', count: '14 tasks'},
  {value: 0.2, label: '20%', count: '27 tasks'},
  {value: 1, label: '100%', count: '134 tasks'},
];

const FUTURE_FIELDS = new Set([
  'actual_duration', 'actual_pickup_at', 'actual_pickup_timestamp',
  'completed_at', 'completion_status', 'is_violation', 'label', 'off_window',
  'outcome', 'pickup_gps_lat', 'pickup_gps_lng', 'pickup_gps_time',
  'pickup_time', 'post_decision_route', 'route_completed_at',
  'route_realization', 'target', 'violated_window', 'violation',
]);

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];

const elements = {
  backToQueue: document.getElementById('back-to-queue'),
  capacityHosts: [...document.querySelectorAll('[data-capacity-control]')],
  feedback: document.getElementById('feedback'),
  feedbackBack: document.getElementById('feedback-back'),
  feedbackKicker: document.getElementById('feedback-kicker'),
  feedbackMessage: document.getElementById('feedback-message'),
  feedbackTitle: document.getElementById('feedback-title'),
  file: document.getElementById('snapshot-file'),
  fileName: document.getElementById('file-name'),
  fileTitle: document.getElementById('file-title'),
  focusContext: document.getElementById('focus-context'),
  focusMeta: document.getElementById('focus-meta'),
  focusTitle: document.getElementById('focus-title'),
  focusWindow: document.getElementById('focus-window'),
  intake: document.getElementById('intake'),
  queue: document.getElementById('queue'),
  queueEmpty: document.getElementById('queue-empty'),
  results: document.getElementById('results'),
  reviewCount: document.getElementById('review-count'),
  run: document.getElementById('run'),
  screenState: document.getElementById('screen-state'),
  status: document.getElementById('status'),
  statusText: document.getElementById('status-text'),
  targetCount: document.getElementById('target-count'),
  taskFocus: document.getElementById('task-focus'),
};

const signalLabels = {
  slack_to_end_h: 'Remaining promise-window buffer',
  pending_other_count: 'Other active pickup commitments',
  pending_overlap_count: 'Overlapping pickup windows',
};

let capacity = 0.1;
let snapshot = null;
let rankedResults = [];
let metadata = null;
let selectedTaskId = null;

function createText(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = value;
  return node;
}

function clearNode(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function setStatus(message, state = 'neutral') {
  elements.status.dataset.state = state;
  elements.statusText.textContent = message;
}

function setScreenState(value) {
  elements.screenState.textContent = `${value} · RC 6d42fbbe`;
}

function showOnly(name) {
  elements.intake.hidden = name !== 'intake';
  elements.results.hidden = name !== 'results';
  elements.taskFocus.hidden = name !== 'focus';
  elements.feedback.hidden = name !== 'feedback';
  document.body.dataset.appState = name;
}

function renderCapacityControls() {
  elements.capacityHosts.forEach(host => {
    clearNode(host);
    const variant = host.dataset.variant || 'control';
    const fieldset = document.createElement('fieldset');
    fieldset.className = 'capacity-control';

    const legend = document.createElement('legend');
    legend.textContent = 'Human review capacity';
    fieldset.appendChild(legend);

    const options = document.createElement('div');
    options.className = 'capacity-options';
    CAPACITIES.forEach(option => {
      const label = document.createElement('label');
      label.className = 'capacity-option';
      label.dataset.selected = String(option.value === capacity);

      const input = document.createElement('input');
      input.className = 'visually-hidden';
      input.type = 'radio';
      input.name = `capacity-${variant}`;
      input.value = String(option.value);
      input.checked = option.value === capacity;
      input.addEventListener('change', () => setCapacity(option.value));

      label.appendChild(input);
      label.appendChild(createText('span', 'capacity-label', option.label));
      label.appendChild(createText('span', 'capacity-count', option.count));
      options.appendChild(label);
    });
    fieldset.appendChild(options);
    fieldset.appendChild(createText('p', 'capacity-note', 'Dispatcher selects the cutoff; task order remains unchanged.'));
    host.appendChild(fieldset);
  });
}

function formatMoment(value) {
  if (typeof value !== 'string') return 'Not available';
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  if (!match) return value.replace('T', ' ');
  const month = MONTHS[Number(match[2]) - 1] || match[2];
  return `${Number(match[3])} ${month} ${match[4]}:${match[5]}`;
}

function windowParts(task) {
  const start = formatMoment(task.window_start).split(' ');
  const end = formatMoment(task.window_end).split(' ');
  return {
    date: start.slice(0, 2).join(' '),
    start: start.at(-1),
    end: end.at(-1),
  };
}

function taskFor(taskId) {
  if (!snapshot || !Array.isArray(snapshot.tasks)) return null;
  return snapshot.tasks.find(task => String(task.task_id) === String(taskId)) || null;
}

function decisionLabel(value) {
  return value === 'WINDOW_REVIEW' ? 'WINDOW REVIEW' : 'KEEP ASSIGNMENT';
}

function appendPromiseInstrument(parent, task) {
  const parts = windowParts(task);
  const instrument = document.createElement('span');
  instrument.className = 'promise-instrument';
  instrument.appendChild(createText('span', 'promise-label', 'Promised window'));

  const axis = document.createElement('span');
  axis.className = 'promise-axis';
  axis.appendChild(createText('span', 'promise-date', parts.date));
  axis.appendChild(createText('span', 'promise-start', parts.start));
  axis.appendChild(createText('span', 'promise-line', ''));
  axis.appendChild(createText('span', 'promise-end', parts.end));
  instrument.appendChild(axis);
  parent.appendChild(instrument);
}

function reviewPrefix() {
  return rankedResults.filter(item => item.decision === 'WINDOW_REVIEW');
}

function renderQueue() {
  clearNode(elements.queue);
  const visible = reviewPrefix();
  elements.queueEmpty.hidden = visible.length !== 0;

  visible.forEach(result => {
    const task = taskFor(result.task_id);
    if (!task) return;
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'queue-item';
    row.dataset.selected = String(String(result.task_id) === String(selectedTaskId));
    row.setAttribute('aria-label', `Rank ${result.rank}, task ${result.task_id}, accepted ${formatMoment(task.accepted_at)}, ${decisionLabel(result.decision)}`);

    row.appendChild(createText('span', 'rank', String(result.rank).padStart(2, '0')));
    const identity = document.createElement('span');
    identity.className = 'task-block';
    identity.appendChild(createText('strong', 'task-id', String(result.task_id)));
    identity.appendChild(createText('span', 'accepted-label', `ACCEPTED · ${formatMoment(task.accepted_at)}`));
    row.appendChild(identity);
    appendPromiseInstrument(row, task);
    row.appendChild(createText('span', 'decision', decisionLabel(result.decision)));
    row.addEventListener('click', () => showTaskFocus(result));
    elements.queue.appendChild(row);
  });
}

function appendContext(label, value) {
  const wrapper = document.createElement('div');
  wrapper.className = 'context-item';
  wrapper.appendChild(createText('dt', '', label));
  wrapper.appendChild(createText('dd', '', value));
  elements.focusContext.appendChild(wrapper);
}

function showTaskFocus(result) {
  const task = taskFor(result.task_id);
  if (!task) return;
  selectedTaskId = result.task_id;
  renderQueue();
  clearNode(elements.focusWindow);
  clearNode(elements.focusContext);

  elements.focusMeta.textContent = `Rank ${String(result.rank).padStart(2, '0')} · ${decisionLabel(result.decision)}`;
  elements.focusTitle.textContent = `Task ${result.task_id}`;
  elements.focusWindow.appendChild(createText('span', 'accepted-label', `ACCEPTED · ${formatMoment(task.accepted_at)}`));
  appendPromiseInstrument(elements.focusWindow, task);

  appendContext('Region', String(task.region_id));
  appendContext('AOI type', String(task.aoi_type));
  appendContext('Accepted', formatMoment(task.accepted_at));
  appendContext('Targets', String(metadata.total_targets));
  (result.evidence_signals || []).forEach(signal => {
    appendContext(signalLabels[signal.signal] || 'Known context', String(signal.value));
  });

  setScreenState('OUTPUT / TASK FOCUS');
  showOnly('focus');
  elements.backToQueue.focus();
}

function renderResults() {
  const visible = reviewPrefix();
  elements.reviewCount.textContent = String(metadata.review_budget_count);
  elements.targetCount.textContent = String(metadata.total_targets);
  selectedTaskId = visible.length ? visible[0].task_id : null;
  renderCapacityControls();
  renderQueue();
  setScreenState(`OUTPUT / CAPACITY ${Math.round(metadata.review_budget_fraction * 100)}%`);
  showOnly('results');
  setStatus('Deterministic ranking complete. Review the queue in rank order.', 'success');
}

function clearResults() {
  rankedResults = [];
  metadata = null;
  selectedTaskId = null;
  clearNode(elements.queue);
  clearNode(elements.focusWindow);
  clearNode(elements.focusContext);
}

function showFeedback(kind, message) {
  const labels = {
    invalid_json: ['INVALID JSON', 'The snapshot could not be read.'],
    invalid_snapshot: ['INVALID SNAPSHOT', 'The snapshot does not match the decision-time contract.'],
    future_field: ['FUTURE DATA REJECTED', 'Only what was knowable then may rank tasks.'],
    model_unavailable: ['MODEL UNAVAILABLE', 'The verified ranking boundary is unavailable.'],
    request_too_large: ['REQUEST TOO LARGE', 'The snapshot exceeds the local-demo request limit.'],
    unavailable: ['REQUEST STOPPED', 'No ranking was produced.'],
  };
  const [kicker, title] = labels[kind] || labels.unavailable;
  elements.feedbackKicker.textContent = kicker;
  elements.feedbackTitle.textContent = title;
  elements.feedbackMessage.textContent = message;
  setScreenState(`INPUT / ${kicker}`);
  showOnly('feedback');
  setStatus(message, 'error');
}

function futureFieldPresent(value) {
  if (!value || typeof value !== 'object') return false;
  if (Array.isArray(value)) return value.some(futureFieldPresent);
  return Object.entries(value).some(([key, child]) => FUTURE_FIELDS.has(key) || futureFieldPresent(child));
}

function responseFailure(status, code) {
  if (status === 413 || code === 'request_too_large') {
    return ['request_too_large', 'This snapshot exceeds the 8 MiB local-demo limit.'];
  }
  if (code === 'model_unavailable') {
    return ['model_unavailable', 'Restore the frozen verified artifact before retrying. No partial result is shown.'];
  }
  if (code === 'invalid_snapshot' || status === 400) {
    return ['invalid_snapshot', 'Check the schema, timestamps, locations, and decision-time fields before retrying.'];
  }
  return ['unavailable', 'KAIROS could not rank this snapshot. No previous result is shown.'];
}

async function runScoring() {
  if (!snapshot) return;
  clearResults();
  showOnly('intake');
  elements.run.disabled = true;
  elements.run.textContent = 'Ranking snapshot…';
  setScreenState('INPUT / PROCESSING');
  setStatus('Ranking accepted pickup promises for the real request duration…', 'loading');
  try {
    snapshot.review_budget_fraction = capacity;
    const response = await fetch('/score', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(snapshot),
    });
    let body = {};
    try {
      body = await response.json();
    } catch (_error) {
      body = {};
    }
    if (!response.ok) throw {status: response.status, code: body.error};
    if (!Array.isArray(body.results) || !body.metadata) throw {status: 500, code: 'invalid_response'};
    rankedResults = body.results;
    metadata = body.metadata;
    renderResults();
  } catch (error) {
    const [kind, message] = responseFailure(error.status, error.code);
    showFeedback(kind, message);
  } finally {
    elements.run.textContent = 'Protect Promises';
    elements.run.disabled = snapshot === null;
  }
}

function setCapacity(value) {
  const wasOutput = !elements.results.hidden || !elements.taskFocus.hidden;
  capacity = value;
  if (snapshot) snapshot.review_budget_fraction = capacity;
  renderCapacityControls();
  if (wasOutput) {
    runScoring();
  } else if (snapshot) {
    setStatus('Capacity updated. Protect promises when the snapshot is ready.', 'ready');
  }
}

elements.file.addEventListener('change', async event => {
  clearResults();
  snapshot = null;
  elements.run.disabled = true;
  const file = event.target.files && event.target.files[0];
  if (!file) {
    elements.fileTitle.textContent = 'Choose a JSON snapshot';
    elements.fileName.textContent = 'Decision-time fields only · future-known values are rejected';
    setStatus('Load a valid snapshot to begin.');
    return;
  }

  setStatus('Reading snapshot…', 'loading');
  try {
    const parsed = JSON.parse(await file.text());
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('invalid');
    if (futureFieldPresent(parsed)) {
      showFeedback('future_field', 'Remove fields that were unavailable at the decision moment, then retry.');
      return;
    }
    snapshot = parsed;
    snapshot.review_budget_fraction = capacity;
    elements.fileTitle.textContent = file.name;
    elements.fileName.textContent = `${parsed.target_task_ids?.length ?? 'Unknown'} target promises · snapshot accepted for request validation`;
    elements.run.disabled = false;
    setScreenState('INPUT / LOADED');
    showOnly('intake');
    setStatus('Snapshot loaded. The server will validate every field before ranking.', 'ready');
  } catch (_error) {
    showFeedback('invalid_json', 'Choose a valid JSON file. No previous result is shown.');
  }
});

elements.run.addEventListener('click', runScoring);

elements.backToQueue.addEventListener('click', () => {
  setScreenState(`OUTPUT / CAPACITY ${Math.round(metadata.review_budget_fraction * 100)}%`);
  showOnly('results');
  const selected = elements.queue.querySelector('[data-selected=true]');
  if (selected) selected.focus();
});

elements.feedbackBack.addEventListener('click', () => {
  showOnly('intake');
  setScreenState(snapshot ? 'INPUT / LOADED' : 'INPUT');
  setStatus(snapshot ? 'Snapshot loaded. Correct the request and retry.' : 'Load a valid snapshot to begin.');
  if (snapshot) elements.run.focus();
  else elements.file.focus();
});

renderCapacityControls();
