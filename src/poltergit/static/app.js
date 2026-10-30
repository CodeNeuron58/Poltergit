"use strict";
const $ = (selector) => document.querySelector(selector);
const token = $('meta[name="poltergit-token"]').content;
let answer = null;
let fileData = null;
let activeLine = 1;
let busy = false;
let loadSequence = 0;
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json', 'X-Poltergit-Token': token},
    body: JSON.stringify(body)
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The request could not be completed. Check the file and line number.');
  return data;
}
function notice(message = '') {
  $('#notice').textContent = message;
  $('#notice').hidden = !message;
}
function sourceLink(source, label) {
  if (source.url && /^https:\/\/github\.com\//.test(source.url)) {
    const link = el('a', 'source-link', label || 'Open original source ↗');
    link.href = source.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
    return link;
  }
  return el('span', 'source-link', source.sha ? `git show ${source.sha.slice(0, 12)}` : 'Local source');
}
function date(value) {
  if (!value) return 'not recorded';
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? 'not recorded' : parsed.toLocaleDateString('en-GB', {day:'2-digit', month:'short', year:'numeric'});
}
function renderCode() {
  const root = $('#code-lines'); root.replaceChildren();
  const lines = fileData.lines;
  const start = lines.length > 2500 ? Math.max(0, activeLine - 121) : 0;
  const end = lines.length > 2500 ? Math.min(lines.length, start + 250) : lines.length;
  const fragment = document.createDocumentFragment();
  for (let i = start; i < end; i++) {
    const row = el('button', 'code-line'); row.type = 'button';
    row.dataset.line = i + 1;
    row.setAttribute('aria-label', `Select line ${i + 1}: ${lines[i]}`);
    row.setAttribute('aria-pressed', String(i + 1 === activeLine));
    if (i + 1 === activeLine) row.classList.add('selected');
    if (/^\s*(#|\/\/|"""|\*\/)/.test(lines[i])) row.classList.add('comment');
    row.append(el('span', 'line-number', String(i + 1)), el('span', '', lines[i] || ' '));
    row.addEventListener('click', () => selectLine(i + 1));
    fragment.append(row);
  }
  root.append(fragment);
  $('#line-count').textContent = `${lines.length} lines${start || end < lines.length ? ` · showing ${start + 1}–${end}` : ''}`;
}
function selectLine(line) {
  activeLine = line;
  $('#target').value = `${fileData.path}:${line}`;
  for (const node of document.querySelectorAll('.code-line.selected')) {
    node.classList.remove('selected'); node.setAttribute('aria-pressed', 'false');
  }
  let selected = document.querySelector(`.code-line[data-line="${line}"]`);
  if (!selected) { renderCode(); selected = document.querySelector(`.code-line[data-line="${line}"]`); }
  if (selected) { selected.classList.add('selected'); selected.setAttribute('aria-pressed', 'true'); }
}
async function loadFile(path, requestedLine) {
  const sequence = ++loadSequence;
  const data = await api(`/api/file?path=${encodeURIComponent(path)}`);
  if (sequence !== loadSequence) return;
  fileData = data;
  const interesting = data.lines.findIndex(line => line.includes('time.sleep(3)'));
  activeLine = requestedLine || (interesting >= 0 ? interesting + 1 : 1);
  $('#file-select').value = path;
  renderCode(); selectLine(activeLine);
  const selected = document.querySelector('.code-line.selected');
  if (selected) $('#code-lines').scrollTop = Math.max(0, selected.offsetTop - $('#code-lines').offsetTop - 130);
}
async function initialize() {
  try {
    const repo = await api('/api/repo');
    $('#repo-name').textContent = repo.name;
    $('#revision').textContent = repo.revision.slice(0, 7);
    $('#record-mode').checked = repo.record_only;
    const select = $('#file-select'); select.replaceChildren();
    for (const path of repo.files) { const option = el('option', '', path); option.value = path; select.append(option); }
    if (repo.files_truncated) notice('The file picker shows the first 3,000 tracked files. You can still enter any tracked file:line above.');
    if (repo.default_file) await loadFile(repo.default_file);
    else notice('This repository has no files at HEAD. Commit a source file first.');
  } catch (error) { notice(error.message); }
}
$('#file-select').addEventListener('change', async (event) => {
  try { await loadFile(event.target.value); notice(); } catch (error) { notice(error.message); }
});

async function typeText(node, text) {
  if (reducedMotion) { node.textContent = text; return; }
  const chunk = Math.max(2, Math.ceil(text.length / 100));
  for (let i = 0; i < text.length; i += chunk) {
    node.textContent = text.slice(0, i + chunk);
    await new Promise(resolve => setTimeout(resolve, 12));
  }
}
function inspectSource(index) {
  const source = $(`#source-${index}`);
  if (source) { source.open = true; source.scrollIntoView({behavior: reducedMotion ? 'instant' : 'smooth', block:'center'}); source.focus(); }
}
function renderEvidence(data) {
  const root = $('#evidence-list'); root.replaceChildren();
  data.history.evidence.forEach((source, index) => {
    const card = el('details', 'evidence-card'); card.id = `source-${index + 1}`; card.tabIndex = -1;
    const summary = el('summary');
    const kicker = el('div', 'evidence-kicker');
    kicker.append(el('span', '', `[${index + 1}] ${source.kind.replace('_', ' ').toUpperCase()}`), el('span', '', date(source.date)));
    summary.append(kicker, el('h3', '', source.title)); card.append(summary);
    const claims = data.claims.filter(c => c.source_id === source.id);
    for (const claim of claims) card.append(el('blockquote', '', claim.quote));
    if (claims.length) card.open = true;
    if (!claims.some(c => c.quote === source.body)) card.append(el('pre', '', source.body));
    if (source.patch) {
      const patch = el('details'); patch.append(el('summary', 'source-date', 'Line history diff'), el('pre', '', source.patch)); card.append(patch);
    }
    card.append(sourceLink(source)); root.append(card);
  });
  $('#source-count').textContent = `${data.history.evidence.length} SOURCES`;
  $('#evidence-section').hidden = false;
}
async function showAnswer(data) {
  answer = data;
  $('#answer-empty').hidden = true; $('#answer-content').hidden = false;
  $('#answer-state').textContent = data.mode === 'ollama' ? 'THE RECORD HAS SPOKEN' : 'SOURCE EXCERPTS';
  $('#speaking-as').textContent = `${data.history.path}:${data.history.line}`;
  const root = $('#answer-text'); root.replaceChildren();
  renderEvidence(data);
  if (data.mode === 'ollama' && data.claims.length) {
    for (const claim of data.claims) {
      const p = el('p'); const text = el('span'); p.append(text); root.append(p);
      await typeText(text, claim.text);
      const index = data.history.evidence.findIndex(s => s.id === claim.source_id) + 1;
      const citation = el('button', 'citation', `[${index}]`); citation.type = 'button';
      citation.setAttribute('aria-label', `Read supporting source ${index}`);
      citation.addEventListener('click', () => inspectSource(index)); p.append(citation);
    }
    if (data.silent) root.append(el('p', '', 'The record is silent about the rest.'));
  } else await typeText(root, data.text);
  $('#answer-meta').textContent = data.mode === 'ollama'
    ? `${data.model} · ${data.input_tokens + data.output_tokens} tokens · $0 inference API cost · quotes matched`
    : 'Source excerpts · no model call · no inferred explanation';
  $('#voice-button').disabled = false; $('#copy-button').disabled = false;
  $('#voice-player').hidden = true; $('#voice-player').pause();
  notice(data.warnings.join('\n'));
}
$('#summon-form').addEventListener('submit', async (event) => {
  event.preventDefault(); if (busy) return;
  const target = $('#target').value.trim();
  if (!/^.+:[1-9]\d*$/.test(target)) { notice('Use a file and positive line number, such as src/client.py:13.'); return; }
  busy = true; notice();
  $('#summon-button').disabled = true; $('#summon-button').textContent = 'Listening to the history…';
  $('#voice-button').disabled = true; $('#copy-button').disabled = true;
  $('#answer-state').textContent = 'WALKING THE RECORD'; $('#answer-state').classList.add('loading-pulse');
  $('#workspace').setAttribute('aria-busy', 'true');
  try {
    const split = target.lastIndexOf(':');
    await loadFile(target.slice(0, split), Number(target.slice(split + 1)));
    const data = await api('/api/why', {target, record: $('#record-mode').checked});
    await showAnswer(data);
  } catch (error) { notice(error.message); $('#answer-state').textContent = 'THE CONNECTION BROKE'; }
  finally {
    busy = false; $('#summon-button').disabled = false;
    $('#summon-button').replaceChildren(document.createTextNode('Begin the séance '), el('span', '', '↗'));
    $('#answer-state').classList.remove('loading-pulse'); $('#workspace').setAttribute('aria-busy', 'false');
  }
});
$('#copy-button').addEventListener('click', async () => {
  if (!answer) return;
  const sources = answer.history.evidence;
  const claims = answer.claims.map(c => `${c.text}\n“${c.quote}”\n${sources.find(s => s.id === c.source_id)?.url || c.source_id}`).join('\n\n');
  try {
    await navigator.clipboard.writeText(`Poltergit — ${answer.history.path}:${answer.history.line}\n${answer.text}\n\n${claims}\n\nMode: ${answer.mode}; HEAD: ${answer.history.revision}`);
    $('#copy-button').textContent = 'Copied with sources ✓';
    setTimeout(() => { $('#copy-button').textContent = 'Copy with sources ↗'; }, 2200);
  } catch { notice('Clipboard access was unavailable. Select the answer and copy it manually.'); }
});
$('#voice-button').addEventListener('click', async () => {
  if (!answer) return;
  $('#voice-button').disabled = true; $('#voice-button').textContent = 'The spirit is finding its voice…';
  try {
    const data = await api('/api/voice', {answer_id: answer.trace_id});
    const player = $('#voice-player'); player.src = data.url; player.hidden = false;
    await player.play();
  } catch (error) { notice(error.message); }
  finally { $('#voice-button').disabled = false; $('#voice-button').textContent = '◖ Hear the spirit'; }
});

function memorialCard(item) {
  const card = el('article', 'memorial');
  card.append(el('div', 'memorial-candle', '✦'), el('div', 'memorial-kind', `In memory of a ${item.kind}`),
    el('h3', '', item.kind === 'file' ? item.name.split('/').pop() : `${item.name}()`), el('p', 'memorial-path', item.path),
    el('p', 'memorial-life', `${date(item.born)} — ${date(item.departed)}`),
    el('p', 'memorial-age', item.days === null ? 'Its age is not recorded.' : `${item.days.toLocaleString()} days of service`),
    el('p', 'memorial-reason', item.reason), sourceLink({url:item.removal_url, sha:item.removal_sha}, 'Read the removal commit ↗'),
    el('p', 'memorial-note', 'Removal message, preserved verbatim.'));
  return card;
}
async function loadMemorials() {
  const root = $('#memorial-list'); root.replaceChildren(el('div', 'loading-text', 'Remembering the departed…'));
  try {
    const data = await api('/api/ofrenda'); root.replaceChildren();
    for (const memorial of data.memorials) root.append(memorialCard(memorial));
    if (!data.memorials.length) root.append(el('p', 'empty-list', 'No departed files or Python functions were found in this history window.'));
  } catch (error) { root.replaceChildren(el('p', 'empty-list', error.message)); }
}
async function loadTraces() {
  const root = $('#trace-list'); root.replaceChildren(el('div', 'loading-text', 'Following the trail…'));
  try {
    const data = await api('/api/traces'); root.replaceChildren();
    for (const [index, trace] of data.traces.entries()) {
      const card = el('details', 'trace-card'); card.open = index === 0;
      const summary = el('summary', '', `${trace.operation.toUpperCase()} / ${trace.status}`);
      summary.append(el('span', '', `${date(trace.timestamp)} · ${Math.round(trace.duration_ms).toLocaleString()} ms`));
      card.append(summary, el('p', 'trace-id', `TRACE ${trace.trace_id}`));
      for (const span of trace.spans) {
        const row = el('div', `span-row ${span.status}`);
        const meter = el('meter', 'span-track'); meter.min = 0; meter.max = Math.max(1, trace.duration_ms);
        meter.value = Math.max(1, span.duration_ms); meter.setAttribute('aria-label', `${span.name}: ${span.duration_ms} milliseconds`);
        row.append(el('span', '', span.name), meter, el('small', '', `${span.duration_ms.toLocaleString()} ms`));
        card.append(row);
        const attrs = Object.entries(span.attributes || {}).map(([k,v]) => `${k.replace('gen_ai.', '')}: ${v}`).join(' · ');
        if (attrs || span.error_type) card.append(el('p', 'span-detail', span.error_type || attrs));
      }
      root.append(card);
    }
    if (!data.traces.length) root.append(el('p', 'empty-list', 'No traces yet. Begin a séance to leave a trail.'));
  } catch (error) { root.replaceChildren(el('p', 'empty-list', error.message)); }
}
for (const button of document.querySelectorAll('[data-view]')) {
  button.addEventListener('click', async () => {
    for (const nav of document.querySelectorAll('[data-view]')) { nav.classList.remove('active'); nav.removeAttribute('aria-current'); }
    button.classList.add('active'); button.setAttribute('aria-current', 'page');
    for (const panel of document.querySelectorAll('.view-panel')) panel.hidden = true;
    $(`#view-${button.dataset.view}`).hidden = false;
    $('#section-title').textContent = {seance:'THE SÉANCE ROOM', ofrenda:'THE OFRENDA', traces:'THE TRACE ARCHIVE'}[button.dataset.view];
    if (button.dataset.view === 'ofrenda') await loadMemorials();
    if (button.dataset.view === 'traces') await loadTraces();
  });
}
$('#refresh-traces').addEventListener('click', loadTraces);
$('#connection-button').addEventListener('click', async () => {
  $('#connection-dialog').showModal();
  try {
    const data = await api('/api/status'); const root = $('#health-list'); root.replaceChildren();
    for (const check of data.checks) {
      const row = el('div', 'health-row');
      row.append(el('strong', '', check.name), el('span', '', check.status), el('p', '', check.detail)); root.append(row);
    }
  } catch (error) { $('#health-list').textContent = error.message; }
});
$('#close-dialog').addEventListener('click', () => $('#connection-dialog').close());
initialize();
