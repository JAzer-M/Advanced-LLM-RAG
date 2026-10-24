// 单个工作台原型：历史结果与实时运行明确区分，引用编号保持后端原顺序。
const $ = (id) => document.getElementById(id);
const icons = {
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10H3V7Z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  chat: '<path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z"/>',
  book: '<path d="M12 5v15M3 4h4a5 5 0 0 1 5 2 5 5 0 0 1 5-2h4v15h-4a5 5 0 0 0-5 2 5 5 0 0 0-5-2H3V4Z"/>',
  history: '<path d="M3 11a9 9 0 1 1 2.4 6M3 4v7h7M12 7v5l3 2"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01"/>',
  panel: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c5 5 5 13 0 18-5-5-5-13 0-18Z"/>',
  'arrow-up': '<path d="M12 19V5m-6 6 6-6 6 6"/>',
  shield: '<path d="m12 3 8 4v5c0 5-8 9-8 9s-8-4-8-9V7l8-4Z"/><path d="m8 12 3 3 5-6"/>',
  copy: '<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
  spark: '<path d="m12 3 2.3 6.7L21 12l-6.7 2.3L12 21l-2.3-6.7L3 12l6.7-2.3L12 3Z"/>',
  quote: '<path d="M10 5H3v8h5c0 4-5 5-5 5M21 5h-7v8h5c0 4-5 5-5 5"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  warning: '<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v4m0 4h.01"/>',
  file: '<path d="M14 2H5v20h14V7l-5-5Z"/><path d="M14 2v5h5M8 12h8M8 16h6"/>',
};
const icon = (name, size = 16) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.file}</svg>`;
const escapeHTML = (text) => String(text ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const format = (number) => number === null || number === undefined ? '—' : Number(number).toLocaleString('zh-CN');
const state = { mode: 'auto', result: null, citedOnly: true, busy: false, meta: null, timer: null, selectedExample: 'flash' };
document.querySelectorAll('[data-icon]').forEach((node) => { node.innerHTML = icon(node.dataset.icon); });

async function api(path, options) {
  const response = await fetch(path, options);
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || '暂时无法连接本地服务。');
  return value;
}

function toast(text) {
  $('toast').textContent = text;
  $('toast').hidden = false;
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => { $('toast').hidden = true; }, 2200);
}

function showError(text) {
  $('message').textContent = text;
  $('message').hidden = !text;
}

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll('[data-mode]').forEach((node) => {
    node.classList.toggle('selected', node.dataset.mode === mode);
    node.setAttribute('aria-pressed', String(node.dataset.mode === mode));
  });
  $('allowNetwork').disabled = mode === 'rag' || state.busy;
  if (mode === 'rag') $('allowNetwork').checked = false;
  $('modeDescription').textContent = {
    rag: '固定流程检索与回答，只使用当前本地知识库。',
    auto: '先用本地证据回答，遇到明确缺口时再升级补查。',
    agent: '逐项检查证据，按需要搜索论文片段或读取相邻原文。',
  }[mode];
}

function inline(text) {
  return escapeHTML(text)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[(\d+)\]/g, (_, n) => {
      if (!state.result?.citations.some((p) => p.number === Number(n))) return `[${n}]`;
      return `<button class="citation-link" data-citation="${n}" aria-label="查看原文引用${n}">${n}</button>`;
    });
}

function markdown(text) {
  // 来源已在独立面板中展示；正文保留原词句和实际引用编号。
  const body = text.split(/\n\n来源[:：]/)[0];
  return body.split(/\n\s*\n/).map((block) => {
    if (/^#{1,3}\s/.test(block)) return `<h3>${inline(block.replace(/^#{1,3}\s*/, ''))}</h3>`;
    if (block.split('\n').every((line) => /^[-*]\s/.test(line))) {
      return `<ul>${block.split('\n').map((line) => `<li>${inline(line.slice(2))}</li>`).join('')}</ul>`;
    }
    return `<p>${block.split('\n').map(inline).join('<br>')}</p>`;
  }).join('');
}

function citedNumbers(result) {
  return new Set([...result.answer.matchAll(/\[(\d+)\]/g)].map((match) => Number(match[1])));
}

function renderSources(selected) {
  const result = state.result;
  if (!result) return;
  const cited = citedNumbers(result);
  const passages = result.citations.filter((item) => !state.citedOnly || cited.has(item.number));
  $('citedOnly').classList.toggle('active', state.citedOnly);
  $('allEvidence').classList.toggle('active', !state.citedOnly);
  $('evidenceCount').textContent = passages.length;
  $('evidenceFooter').textContent = `共选入 ${result.citations.length} 段证据 · ${cited.size} 段在回答中引用。`;
  $('sourceList').innerHTML = passages.length ? passages.map((item) => `
    <article class="source-card ${selected === item.number ? 'selected expanded' : ''}" id="source-${item.number}" tabindex="-1">
      <div class="source-top"><span class="source-number">${item.number}</span><span class="source-title">${escapeHTML(item.title || item.source)}</span></div>
      <div class="source-meta"><span>第 ${escapeHTML(item.page)} 页</span><span>${item.origin === 'arxiv' ? 'arXiv原文' : '本地论文'}</span></div>
      <p class="source-text">${escapeHTML(item.text)}</p>
      <div class="source-bottom"><button data-expand="${item.number}">${selected === item.number ? '收起片段' : '展开片段'} ↗</button>${item.url ? `<a href="${escapeHTML(item.url)}" target="_blank" rel="noopener noreferrer">固定版本 PDF ↗</a>` : `<span class="source-kind">${escapeHTML(item.source)}</span>`}</div>
    </article>`).join('') : '<div class="source-empty">这次回答没有引用事实性原文。<br>可切换“全部证据”查看已取得的本地片段。</div>';
}

function renderActivity(result) {
  const labels = {search: '搜索本地知识库', read_neighbors: '读取相邻原文', search_arxiv: '搜索arXiv原论文', read_arxiv_paper: '读取固定版本PDF'};
  const external = result.citations.filter((item) => item.origin === 'arxiv').length;
  const rows = [{title: '检索论文证据', detail: `本地 ${result.citations.length - external} 段${external ? `，追加外部原文 ${external} 段` : ''}。`}];
  result.actions.forEach((action) => rows.push({title: labels[action.tool] || action.tool,
    detail: action.status === 'failed' ? '本次获取未完成，失败记录已保留。' : '本次行动已完成。', warning: action.status === 'failed'}));
  const reviews = {review_passed: '通过自动复核', insufficient_evidence: '当前证据不足', source_unavailable: '外部来源暂时不可用', review_failed: '回答未通过复核', not_reviewed: '完成引用结构检查', unavailable: '本次处理未完成', citation_failed: '引用检查未通过'};
  const stops = {external_timeout: '外部搜索或读取超时，本轮未自动重试。', external_rate_limited: '外部服务限流，本轮未自动重试。',
    external_http_error: '外部服务返回错误，本轮未自动重试。', external_transport_error: '外部连接失败，本轮未自动重试。',
    action_budget: '本轮工具行动预算已用完。', api_budget: '本轮模型调用预算已用完。', context_budget: '本轮原文容量已达到上限。'};
  rows.push({title: reviews[result.answer_status] || result.answer_status,
    detail: stops[result.stop_reason] || (result.status === 'degraded' ? '保留有限交付，尚未核实的内容不作为事实答案。' : '回答状态与原始运行记录一致。'),
    warning: result.status !== 'completed'});
  $('activityCount').textContent = rows.length;
  $('activityView').innerHTML = rows.map((row) => `<div class="activity-row ${row.warning ? 'warning' : ''}"><strong>${escapeHTML(row.title)}</strong><p>${escapeHTML(row.detail)}</p></div>`).join('');
}

function renderResult(result) {
  state.result = result;
  state.citedOnly = true;
  $('resultSection').hidden = false;
  $('emptyState').hidden = true;
  const warning = result.status !== 'completed';
  $('resultStatus').className = `result-status ${result.status === 'failed' ? 'failed' : warning ? 'warning' : ''}`;
  $('resultStatus').innerHTML = `${icon(warning ? 'warning' : 'check')}<span>${{completed: '回答已完成', degraded: '部分完成 · 来源不可用', failed: '本次处理未完成'}[result.status] || result.status}</span>`;
  $('originLabel').textContent = result.origin === 'saved' ? '历史真实记录' : '本次实时运行';
  $('runMeta').textContent = `${result.date || new Date().toLocaleDateString('zh-CN')} · ${result.mode.toUpperCase()} · ${result.network.papers_read ? '含外部原文' : '本地证据'}`;
  $('answerLabel').textContent = warning ? '本次结果与待核实需求' : '基于论文原文的回答';
  $('answerBody').innerHTML = markdown(result.answer);
  $('answerNote').className = `answer-disclaimer ${warning ? 'warning' : ''}`;
  const note = result.origin === 'saved' ? '正在查看已保存的真实运行结果，本次回放没有调用模型。' : '本次回答使用现有后端生成。重要结论可以点击编号核对原文。';
  $('answerNote').innerHTML = icon(warning ? 'shield' : 'history') + `<span>${note}${warning ? ' 外部获取失败不代表论文未报告所问内容。' : ''}</span>`;
  const usage = result.api_summary.reported_usage || {};
  const historical = result.origin === 'saved';
  $('metrics').innerHTML = [
    {label: historical ? '原运行模型调用' : '模型调用', value: format(result.api_summary.attempts), unit: '次'},
    {label: historical ? '原运行 Token' : 'Token 用量', value: format(usage.total_tokens), unit: ''},
    {label: historical ? '原运行耗时' : '本次耗时', value: result.elapsed === null ? '—' : format(Math.round(result.elapsed * 10) / 10), unit: 's'},
  ].map((metric) => `<div class="metric"><span class="metric-label">${metric.label}</span><span class="metric-value">${metric.value}<small>${metric.unit}</small></span></div>`).join('');
  renderSources();
  renderActivity(result);
  showTab('answer');
}

function showTab(name) {
  const answer = name === 'answer';
  $('answerTab').classList.toggle('active', answer);
  $('activityTab').classList.toggle('active', !answer);
  $('answerTab').setAttribute('aria-selected', String(answer));
  $('activityTab').setAttribute('aria-selected', String(!answer));
  $('answerView').hidden = !answer;
  $('activityView').hidden = answer;
}

async function loadExample(identity) {
  if (state.busy) return;
  try {
    showError('');
    const result = await api(`/api/examples/${identity}`);
    state.selectedExample = identity;
    $('query').value = result.query;
    document.querySelectorAll('.example-item').forEach((item) => item.classList.toggle('active', item.dataset.example === identity));
    renderResult(result);
  } catch (error) { showError(error.message); }
}

function setBusy(busy) {
  state.busy = busy;
  $('query').disabled = busy;
  $('runButton').disabled = busy || !state.meta?.configured;
  $('runButton').innerHTML = icon(busy ? 'history' : 'arrow-up', 13) + `<span>${busy ? '正在回答' : '运行问题'}</span>`;
  $('runningPanel').hidden = !busy;
  document.querySelectorAll('[data-mode],[data-example],#newQuestion').forEach((node) => { node.disabled = busy; });
  setMode(state.mode);
}

async function pollJob(identity) {
  try {
    const job = await api(`/api/jobs/${identity}`);
    if (job.status === 'running') {
      $('runningTime').textContent = `${job.elapsed.toFixed(1)}s`;
      state.timer = setTimeout(() => pollJob(identity), 1000);
      return;
    }
    setBusy(false);
    renderResult(job.result);
    toast(job.result.status === 'completed' ? '本次运行已完成' : '本次结果已返回，请查看状态说明');
  } catch (error) {
    setBusy(false);
    showError(error.message + ' 页面重新连接不会自动重跑问题。');
  }
}

$('queryForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (state.busy) return;
  const query = $('query').value.trim();
  if (!query) { showError('先输入一个你想了解的问题。'); $('query').focus(); return; }
  try {
    showError('');
    const job = await api('/api/run', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query, mode: state.mode, allow_network: $('allowNetwork').checked})});
    $('resultSection').hidden = true;
    $('emptyState').hidden = true;
    $('runningTime').textContent = '0.0s';
    document.querySelectorAll('.example-item').forEach((item) => item.classList.remove('active'));
    setBusy(true);
    pollJob(job.id);
  } catch (error) { showError(error.message); }
});

document.addEventListener('click', (event) => {
  const mode = event.target.closest('[data-mode]');
  if (mode) setMode(mode.dataset.mode);
  const example = event.target.closest('[data-example]');
  if (example) loadExample(example.dataset.example);
  const reference = event.target.closest('[data-citation]');
  if (reference) {
    const number = Number(reference.dataset.citation);
    state.citedOnly = true;
    renderSources(number);
    const source = $(`source-${number}`);
    source?.scrollIntoView({behavior: 'smooth', block: 'nearest'});
    source?.focus({preventScroll: true});
  }
  const expand = event.target.closest('[data-expand]');
  if (expand) {
    const card = $(`source-${expand.dataset.expand}`);
    const expanded = card.classList.toggle('expanded');
    expand.textContent = expanded ? '收起片段 ↗' : '展开片段 ↗';
  }
});

document.addEventListener('keydown', (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter' && !state.busy) $('queryForm').requestSubmit();
});
$('answerTab').onclick = () => showTab('answer');
$('activityTab').onclick = () => showTab('activity');
$('citedOnly').onclick = () => { state.citedOnly = true; renderSources(); };
$('allEvidence').onclick = () => { state.citedOnly = false; renderSources(); };
$('copyAnswer').onclick = async () => {
  if (!state.result) return;
  try { await navigator.clipboard.writeText(state.result.answer); toast('答案已复制'); }
  catch { toast('浏览器未允许复制，可以直接选中答案文本。'); }
};
$('newQuestion').onclick = () => {
  if (state.busy) return;
  $('query').value = '';
  $('resultSection').hidden = true;
  $('emptyState').hidden = false;
  state.result = null;
  showError('');
  document.querySelectorAll('.example-item').forEach((item) => item.classList.remove('active'));
  $('query').focus();
};
$('workspaceButton').onclick = () => window.scrollTo({top: 0, behavior: 'smooth'});
$('closeDialog').onclick = () => $('infoDialog').close();
$('infoDialog').addEventListener('click', (event) => { if (event.target === $('infoDialog')) $('infoDialog').close(); });
$('catalogButton').onclick = () => {
  if (!state.meta) return;
  $('dialogTitle').textContent = `我的知识库 · ${state.meta.papers.length} 篇论文`;
  $('dialogContent').innerHTML = state.meta.papers.map((paper) => `<div class="catalog-item">${icon('book')}<div><strong>${escapeHTML(paper.title)}</strong><small>${paper.chunks} 段原文 · ${escapeHTML(paper.source)}</small></div></div>`).join('');
  $('infoDialog').showModal();
};
$('mobileCatalog').onclick = () => $('catalogButton').click();
$('helpButton').onclick = () => {
  $('dialogTitle').textContent = '开始使用 PaperLens';
  $('dialogContent').innerHTML = '<p>先点击左侧案例或快捷入口，查看已有的真实回答与引用。历史回放不会调用模型，页面会明确标注原运行时间和成本。</p><p>输入自己的问题后，选择模式并点击“运行问题”，会调用你已配置的模型API。联网补证据默认关闭，固定RAG只用本地论文。</p><p>点击答案中的引用编号可以定位原文；“运行过程”展示实际行动和停止状态。来源不可用时，保留已知内容和未核实需求。</p>' + `<p>当前知识库 ${state.meta?.papers.length || 8} 篇论文，${format(state.meta?.chunks)} 段原文。${state.meta?.configured ? '模型已配置：' + escapeHTML(state.meta.model) : '模型API尚未配置。'}</p>`;
  $('infoDialog').showModal();
};

async function init() {
  try {
    state.meta = await api('/api/meta');
    $('kbSummary').textContent = `${state.meta.papers.length} 篇论文 · ${format(state.meta.chunks)} 段原文`;
    $('paperCount').textContent = state.meta.papers.length;
    $('exampleList').innerHTML = state.meta.examples.map((example) => `<button class="example-item ${example.id === 'flash' ? 'active' : ''}" data-example="${example.id}">${icon('chat')}<span><strong>${escapeHTML(example.title)}</strong><small>${example.date} · ${escapeHTML(example.tag)}</small></span></button>`).join('');
    setBusy(false);
    if (!state.meta.configured) showError('本地模型API尚未配置。你可以先查看历史案例。');
    await loadExample('flash');
  } catch (error) { showError(error.message); }
}
init();
