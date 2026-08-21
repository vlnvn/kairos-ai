'use strict';

const elements = {
  capacity: document.getElementById('capacity'),
  detail: document.getElementById('detail'),
  file: document.getElementById('snapshot-file'),
  fileName: document.getElementById('file-name'),
  filterAll: document.getElementById('filter-all'),
  filterReview: document.getElementById('filter-review'),
  queue: document.getElementById('queue'),
  queueEmpty: document.getElementById('queue-empty'),
  results: document.getElementById('results'),
  run: document.getElementById('run'),
  status: document.getElementById('status'),
  statusText: document.getElementById('status-text'),
  summary: document.getElementById('summary'),
  summaryMeta: document.getElementById('summary-meta'),
};

const signalLabels = {
  slack_to_end_h: 'Remaining promise-window buffer',
  pending_other_count: 'Other active pickup commitments',
  pending_overlap_count: 'Overlapping pickup windows',
};

let snapshot = null;
let results = [];
let selectedTaskId = null;
let activeFilter = 'review';

function setStatus(message, state = 'neutral') {
  elements.status.dataset.state = state;
  elements.statusText.textContent = message;
}

function clearNode(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function clearResults() {
  results = [];
  selectedTaskId = null;
  elements.results.hidden = true;
  clearNode(elements.queue);
  clearNode(elements.detail);
}

function formatTimestamp(value) {
  if (typeof value !== 'string') return 'Not available';
  return value.replace('T', ' ').replace(/:00(?:Z|[+-]\d\d:\d\d)?$/, '');
}

function formatWindow(task) {
  return `${formatTimestamp(task.window_start)} — ${formatTimestamp(task.window_end)}`;
}

function taskFor(taskId) {
  return snapshot.tasks.find(task => String(task.task_id) === String(taskId));
}

function decisionLabel(decision) {
  return decision === 'WINDOW_REVIEW' ? 'WINDOW REVIEW' : 'KEEP ASSIGNMENT';
}

function createTextElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  return element;
}

function renderDetail(result) {
  clearNode(elements.detail);
  if (!result) {
    elements.detail.appendChild(
      createTextElement('p', 'empty-message', 'Select a ranked promise to inspect known operational context.')
    );
    return;
  }

  const task = taskFor(result.task_id);
  const review = result.decision === 'WINDOW_REVIEW';
  elements.detail.appendChild(createTextElement('p', 'detail-rank', `Priority rank ${result.rank}`));
  elements.detail.appendChild(createTextElement('h3', 'detail-id', String(result.task_id)));
  const decision = createTextElement('div', `detail-decision ${review ? 'review' : 'keep'}`, decisionLabel(result.decision));
  elements.detail.appendChild(decision);

  const facts = document.createElement('dl');
  facts.className = 'fact-list';
  const factValues = [
    ['Accepted', formatTimestamp(task.accepted_at)],
    ['Promised window', formatWindow(task)],
    ['Region', String(task.region_id)],
    ['Area type', String(task.aoi_type)],
  ];
  factValues.forEach(([label, value]) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'fact';
    wrapper.appendChild(createTextElement('dt', '', label));
    wrapper.appendChild(createTextElement('dd', '', value));
    facts.appendChild(wrapper);
  });
  elements.detail.appendChild(facts);

  elements.detail.appendChild(createTextElement('h4', 'signal-heading', 'Known operational context'));
  const signals = document.createElement('ul');
  signals.className = 'signal-list';
  result.evidence_signals.forEach(signal => {
    const item = document.createElement('li');
    item.className = 'signal-item';
    item.appendChild(
      createTextElement('span', '', signalLabels[signal.signal] || 'Approved context signal')
    );
    item.appendChild(createTextElement('span', 'signal-value', String(signal.value)));
    signals.appendChild(item);
  });
  elements.detail.appendChild(signals);
  elements.detail.appendChild(
    createTextElement(
      'p',
      'notice',
      'This ordering uses non-causal operational signals. A dispatcher owns every review and action.'
    )
  );
}

function visibleResults() {
  return activeFilter === 'review'
    ? results.filter(result => result.decision === 'WINDOW_REVIEW')
    : results;
}

function renderQueue() {
  clearNode(elements.queue);
  const visible = visibleResults();
  elements.queueEmpty.hidden = visible.length !== 0;

  if (!visible.some(result => String(result.task_id) === String(selectedTaskId))) {
    selectedTaskId = visible.length ? visible[0].task_id : null;
  }

  visible.forEach(result => {
    const task = taskFor(result.task_id);
    const button = document.createElement('button');
    const review = result.decision === 'WINDOW_REVIEW';
    button.type = 'button';
    button.className = 'queue-item';
    button.dataset.taskId = String(result.task_id);
    button.setAttribute('aria-current', String(String(result.task_id) === String(selectedTaskId)));
    button.setAttribute('aria-label', `Rank ${result.rank}, task ${result.task_id}, ${decisionLabel(result.decision)}`);

    const identity = document.createElement('span');
    identity.className = 'rank-task';
    identity.appendChild(createTextElement('span', 'rank', String(result.rank).padStart(2, '0')));
    identity.appendChild(createTextElement('span', 'task-id', String(result.task_id)));
    button.appendChild(identity);
    button.appendChild(createTextElement('span', 'window', formatWindow(task)));
    button.appendChild(
      createTextElement('span', `decision ${review ? 'review' : 'keep'}`, decisionLabel(result.decision))
    );
    button.addEventListener('click', () => {
      selectedTaskId = result.task_id;
      renderQueue();
    });
    elements.queue.appendChild(button);
  });

  renderDetail(results.find(result => String(result.task_id) === String(selectedTaskId)));
}

function renderResults(metadata) {
  const reviewCount = results.filter(result => result.decision === 'WINDOW_REVIEW').length;
  const noun = reviewCount === 1 ? 'promise needs' : 'promises need';
  elements.summary.textContent = `${reviewCount} of ${metadata.total_targets} pickup ${noun} priority review.`;
  elements.summaryMeta.textContent = `${Math.round(metadata.review_budget_fraction * 100)}% review capacity · snapshot ${formatTimestamp(snapshot.snapshot_time)}`;
  elements.results.hidden = false;
  activeFilter = 'review';
  elements.filterReview.setAttribute('aria-pressed', 'true');
  elements.filterAll.setAttribute('aria-pressed', 'false');
  selectedTaskId = results.length ? results[0].task_id : null;
  renderQueue();
}

function errorMessage(status, code) {
  if (status === 413 || code === 'request_too_large') return 'This snapshot exceeds the 8 MiB local-demo limit.';
  if (code === 'invalid_snapshot' || status === 400) return 'Snapshot rejected. Check its schema, timestamps, locations, and decision-time fields.';
  if (code === 'model_unavailable') return 'The verified model is unavailable. Restore the frozen artifact before retrying.';
  return 'KAIROS could not score this snapshot. No previous results are shown.';
}

elements.file.addEventListener('change', async event => {
  clearResults();
  snapshot = null;
  elements.run.disabled = true;
  const file = event.target.files && event.target.files[0];
  elements.fileName.textContent = file ? file.name : 'No file selected';
  if (!file) {
    setStatus('Load a valid snapshot to begin.');
    return;
  }
  setStatus('Reading snapshot…', 'loading');
  try {
    const parsed = JSON.parse(await file.text());
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('invalid');
    snapshot = parsed;
    snapshot.review_budget_fraction = Number(elements.capacity.value);
    elements.run.disabled = false;
    setStatus(`Snapshot ready · ${parsed.target_task_ids?.length ?? 'unknown'} target promises found.`, 'ready');
  } catch (_error) {
    snapshot = null;
    setStatus('Invalid JSON. Choose a valid KAIROS snapshot file.', 'error');
  }
});

elements.capacity.addEventListener('change', () => {
  clearResults();
  if (snapshot) {
    snapshot.review_budget_fraction = Number(elements.capacity.value);
    setStatus('Capacity updated. Protect promises to refresh the queue.', 'ready');
  }
});

elements.run.addEventListener('click', async () => {
  if (!snapshot) return;
  clearResults();
  elements.run.disabled = true;
  const originalLabel = elements.run.firstElementChild.textContent;
  elements.run.firstElementChild.textContent = 'Scoring…';
  setStatus('Scoring accepted pickup promises…', 'loading');
  try {
    snapshot.review_budget_fraction = Number(elements.capacity.value);
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
    results = body.results;
    renderResults(body.metadata);
    setStatus('Deterministic ranking complete. Review the queue in rank order.', 'success');
  } catch (error) {
    clearResults();
    setStatus(errorMessage(error.status, error.code), 'error');
  } finally {
    elements.run.firstElementChild.textContent = originalLabel;
    elements.run.disabled = snapshot === null;
  }
});

elements.filterReview.addEventListener('click', () => {
  activeFilter = 'review';
  elements.filterReview.setAttribute('aria-pressed', 'true');
  elements.filterAll.setAttribute('aria-pressed', 'false');
  renderQueue();
});

elements.filterAll.addEventListener('click', () => {
  activeFilter = 'all';
  elements.filterReview.setAttribute('aria-pressed', 'false');
  elements.filterAll.setAttribute('aria-pressed', 'true');
  renderQueue();
});
