// 配置只提交本机；密钥不回填、不进入浏览器存储。
const $ = (id) => document.getElementById(id);
const paths = {
  'arrow-up-right': '<path d="M6 18 18 6M6 6h12v12"/>',
  stack: '<path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>',
  layers: '<rect x="4" y="4" width="12" height="12" rx="2"/><path d="M8 20h12V8M8 8h4M8 12h4"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c5 5 5 13 0 18-5-5-5-13 0-18Z"/>',
  shield: '<path d="m12 3 8 4v5c0 5-8 9-8 9s-8-4-8-9V7l8-4Z"/><path d="m8 12 3 3 5-6"/>',
  book: '<path d="M12 5v15M3 4h4a5 5 0 0 1 5 2 5 5 0 0 1 5-2h4v15h-4a5 5 0 0 0-5 2 5 5 0 0 0-5-2H3V4Z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  copy: '<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
};
const icon = (name) => `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.info}</svg>`;
const escapeHTML = (text) => String(text ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const format = (n) => n == null ? '—' : Number(n).toLocaleString('zh-CN');
const state = {mode:'auto', meta:null, result:null, busy:false, loading:false, activeJob:null, citedOnly:true, selected:null, exampleRequest:0, timer:null};
const sessionKey = 'paperlens.webui.session';
document.querySelectorAll('[data-icon]').forEach((el) => { el.innerHTML = icon(el.dataset.icon); });

// sessionStorage 只记当前页签的草稿/任务编号；不可用时仍可正常提问。
function remember(view = {}) {
  try { sessionStorage.setItem(sessionKey, JSON.stringify({query:$('question').value, mode:state.mode, network:$('network').checked, ...view})); } catch {}
}
function recall() { try { return JSON.parse(sessionStorage.getItem(sessionKey) || '{}'); } catch { return {}; } }
function connection(ok) {
  $('connection').className = `connection ${ok ? 'online' : 'offline'}`;
  $('connection').innerHTML = `<i></i><span>${ok ? '本地已连接' : '连接中断'}</span>`;
}
async function api(path, options = {}) {
  let response;
  try { response = await fetch(path, {...options, signal:AbortSignal.timeout(15000)}); }
  catch { connection(false); throw new Error('暂时无法连接本地服务。请确认启动终端仍在运行。'); }
  const value = await response.json();
  connection(true);
  if (!response.ok) { const error = new Error(value.error || '本次请求未完成。'); error.status = response.status; throw error; }
  return value;
}
function notice(message = '', reconnect = false) {
  $('noticeText').textContent = message;
  $('notice').hidden = !message;
  $('retryConnection').hidden = !reconnect;
}
function toast(message) {
  $('toast').textContent = message; $('toast').hidden = false;
  clearTimeout(state.toastTimer); state.toastTimer = setTimeout(() => { $('toast').hidden = true; }, 2600);
}
function syncControls() {
  const locked = state.busy || state.loading;
  $('question').disabled = locked;
  $('submitButton').disabled = locked || !state.meta?.configured;
  $('submitButton').innerHTML = `<span>${state.busy ? '正在探究' : state.loading ? '读取记录' : '开始探究'}</span>${icon(state.busy ? 'clock' : 'arrow-up-right')}`;
  document.querySelectorAll('[data-mode],[data-example],#newQuestion,#homeButton,#editQuestion,#configButton').forEach((el) => { el.disabled = locked; });
  $('network').disabled = locked || state.mode === 'rag';
  document.querySelectorAll('[data-mode]').forEach((el) => {
    const selected = el.dataset.mode === state.mode;
    el.classList.toggle('selected', selected); el.setAttribute('aria-pressed', selected);
  });
  $('modeHint').textContent = {
    auto:'先回答，遇到明确证据缺口时再补查。',
    rag:'固定检索与回答，只使用本地论文；通常更直接。',
    agent:'逐项检查需求，按需检索或读取相邻原文。',
  }[state.mode];
  $('network').closest('label').title = state.mode === 'rag' ? 'RAG 只使用本地论文；Auto / Agent 可以开启 arXiv。' : '本地证据不足时，允许搜索并读取一篇 arXiv 原论文。';
}
function setMode(mode) {
  if (!['auto','rag','agent'].includes(mode)) return;
  state.mode = mode;
  if (mode === 'rag') $('network').checked = false;
  syncControls();
}

// 小型安全 Markdown 渲染：先转义文字；支持论文回答常见的列表、表格和引用编号。
function inline(text) {
  return String(text).split(/(`[^`]+`|\[[^\]\n]+\]\(https?:\/\/[^)\s]+\))/g).map((part) => {
    if (part.startsWith('`') && part.endsWith('`')) return `<code>${escapeHTML(part.slice(1,-1))}</code>`;
    const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/);
    if (link) return `<a href="${escapeHTML(link[2])}" target="_blank" rel="noopener noreferrer">${escapeHTML(link[1])} ↗</a>`;
    return escapeHTML(part).replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/\[(\d+)\]/g, (raw, n) => {
      if (!state.result?.citations.some((c) => c.number === Number(n))) return raw;
      const display = displayNumber(Number(n));
      return `<button class="citation" data-citation="${n}" title="原始引用 [${n}]" aria-label="查看引用 ${display} 的原文，原始编号 ${n}">[${display}]</button>`;
    });
  }).join('');
}
function markdown(text) {
  const lines = String(text).split('\n'), html = [];
  for (let i=0; i<lines.length;) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    if (/^#{1,6}\s/.test(line)) { html.push(`<h3>${inline(line.replace(/^#{1,6}\s+/,''))}</h3>`); i++; continue; }
    if (line.startsWith('```')) {
      const code=[]; i++; while(i<lines.length && !lines[i].startsWith('```')) code.push(lines[i++]);
      html.push(`<pre><code>${escapeHTML(code.join('\n'))}</code></pre>`); i++; continue;
    }
    if (i+1<lines.length && line.includes('|') && /^\s*\|?\s*:?-{3,}/.test(lines[i+1])) {
      const cells = (row) => row.trim().replace(/^\||\|$/g,'').split('|');
      const head = cells(line); i+=2; const rows=[];
      while(i<lines.length && lines[i].includes('|') && lines[i].trim()) rows.push(cells(lines[i++]));
      html.push(`<div class="table-wrap"><table><thead><tr>${head.map(c=>`<th>${inline(c)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(c=>`<td>${inline(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`); continue;
    }
    const list = line.match(/^\s*(?:([-*])|(\d+)\.)\s+/);
    if (list) {
      const tag=list[2]?'ol':'ul', items=[];
      const pattern=tag==='ol'?/^\s*\d+\.\s+/:/^\s*[-*]\s+/;
      while(i<lines.length && pattern.test(lines[i])) items.push(`<li>${inline(lines[i++].replace(pattern,''))}</li>`);
      html.push(`<${tag}>${items.join('')}</${tag}>`); continue;
    }
    if (/^>\s?/.test(line)) { html.push(`<blockquote>${inline(line.replace(/^>\s?/,''))}</blockquote>`); i++; continue; }
    const paragraph=[line]; i++;
    while(i<lines.length && lines[i].trim() && !/^(?:#{1,6}\s|[-*]\s|\d+\.\s|>|```)/.test(lines[i]) && !(i+1<lines.length && /^\s*\|?\s*:?-{3,}/.test(lines[i+1]))) paragraph.push(lines[i++]);
    html.push(`<p>${paragraph.map(inline).join('<br>')}</p>`);
  }
  return html.join('');
}
function citedNumbers() { return new Set([...state.result.answer.matchAll(/\[(\d+)\]/g)].map(m=>Number(m[1])).filter(n=>state.result.citations.some(c=>c.number===n))); }
function displayNumber(original) {
  const ordered = [...citedNumbers(), ...state.result.citations.map(c=>c.number)];
  return [...new Set(ordered)].indexOf(original) + 1;
}
function compactQuestion() {
  $('questionBar').hidden=false;
  $('compactQuestion').textContent=$('question').value;
  $('compactQuestion').title=$('question').value;
  document.body.classList.remove('editing');
  $('editQuestion').setAttribute('aria-expanded','false');
}
function renderSources() {
  const result=state.result; if(!result) return;
  const cited=citedNumbers();
  const sources=result.citations.filter(c=>!state.citedOnly || cited.has(c.number)).sort((a,b)=>displayNumber(a.number)-displayNumber(b.number));
  $('evidenceCount').textContent=sources.length;
  $('citedButton').classList.toggle('selected',state.citedOnly); $('citedButton').setAttribute('aria-pressed',state.citedOnly);
  $('allButton').classList.toggle('selected',!state.citedOnly); $('allButton').setAttribute('aria-pressed',!state.citedOnly);
  $('sources').innerHTML=sources.map(c=>`<article class="source-card ${state.selected===c.number?'selected expanded':''}" id="source-${c.number}" tabindex="-1"><div class="source-header"><span class="source-number" title="原始引用 [${c.number}]">[${displayNumber(c.number)}]</span><span class="source-name">${escapeHTML(c.title||c.source)}</span></div><div class="source-meta"><span>${c.page == null ? '页码未提供' : `第 ${escapeHTML(c.page)} 页`}</span><span>${c.origin==='arxiv'?'arXiv 原论文':'本地论文'}</span></div><p class="source-text" id="passage-${c.number}">${escapeHTML(c.text)}</p><div class="source-bottom"><button data-expand="${c.number}" aria-expanded="${state.selected===c.number}" aria-controls="passage-${c.number}">${state.selected===c.number?'收起原文 −':'展开原文 +'}</button>${c.url?.startsWith('https://arxiv.org/')?`<a href="${escapeHTML(c.url)}" target="_blank" rel="noopener noreferrer">论文 PDF ↗</a>`:''}</div></article>`).join('') || '<div class="empty-sources">这次结果没有引用事实性原文。<br>可以切换“全部证据”，查看已取得的片段。</div>';
  $('sourcesNote').textContent=`共 ${result.citations.length} 段证据，回答引用了 ${cited.size} 段。显示编号按首次引用排序；悬停编号可查看原始编号。`;
}
function renderActivity(result) {
  const labels={search:'检索本地论文',read_neighbors:'读取相邻原文',search_arxiv:'搜索 arXiv 原论文',read_arxiv_paper:'读取固定版本 PDF'};
  const reviews={review_passed:'通过自动复核',not_reviewed:'完成引用结构检查',insufficient_evidence:'证据不足，已说明缺口',source_unavailable:'外部原文暂时无法获取',review_failed:'回答未通过复核',citation_failed:'引用检查未通过',unavailable:'未形成可交付回答'};
  const external=result.citations.filter(c=>c.origin==='arxiv').length;
  const rows=[{title:'取得论文片段',detail:`本地 ${result.citations.length-external} 段，外部 ${external} 段。`}];
  for(const action of result.actions) rows.push({title:labels[action.tool]||action.tool,detail:action.status==='failed'?'行动未完成，失败记录已保留。':action.status==='completed'?'行动完成。':`记录状态：${action.status}`,warning:action.status==='failed'});
  const stops={external_timeout:'外部请求超时，未自动重试。',external_rate_limited:'外部服务限流，未自动重试。',external_http_error:'外部请求出错，未自动重试。',external_transport_error:'外部连接失败，未自动重试。',action_budget:'工具行动达到本轮预算。',api_budget:'模型调用达到本轮预算。'};
  rows.push({title:reviews[result.answer_status]||'处理结束',detail:stops[result.stop_reason]||`停止原因：${result.stop_reason||'未提供'}。自动检查不等于独立事实验收。`,warning:result.status!=='completed'});
  $('activities').innerHTML=rows.map(r=>`<li class="${r.warning?'warning':''}"><strong>${escapeHTML(r.title)}</strong><p>${escapeHTML(r.detail)}</p></li>`).join('');
}
function showTab(name) {
  for(const key of ['answer','activity']) {
    const selected=key===name; $(key+'Tab').classList.toggle('active',selected);
    $(key+'Tab').setAttribute('aria-selected',selected); $(key+'Tab').tabIndex=selected?0:-1; $(key+'View').hidden=!selected;
  }
}
function renderResult(result) {
  state.result=result; state.citedOnly=true; state.selected=null;
  compactQuestion(); document.body.classList.add('reading'); $('running').hidden=true; $('result').hidden=false;
  $('resultQuestion').textContent=result.query;
  $('runSummary').textContent=`执行路径 ${result.route||result.mode.toUpperCase()} · ${result.local_coverage?`本地检查支持 ${result.local_coverage.supported}/${result.local_coverage.total} 项需求（不含后续联网补证据）`:'本地需求覆盖未提供'} · 知识库 ${result.kb_version} · 已记录 ${result.actions.length} 项工具行动 · arXiv 请求 ${result.network?.http_tool_calls||0} 次`;
  $('resultOrigin').textContent=result.origin==='saved'?'历史回放 · 未调用模型':'本次实时运行';
  $('resultMode').textContent=`${result.mode.toUpperCase()}${result.date?' / '+result.date:''}`;
  const label=result.status==='failed'?'本次处理未完成':result.answer_status==='source_unavailable'?'外部论文暂时不可用':result.status==='degraded'?'部分完成':result.answer_status==='insufficient_evidence'?'证据不足，已说明缺口':'回答已生成';
  $('resultStatus').className=`status-tag ${result.status==='failed'?'failed':result.status==='degraded'?'warning':''}`;
  $('resultStatus').innerHTML=icon(result.status==='completed'?'check':'info')+escapeHTML(label);
  $('answer').innerHTML=markdown(result.answer);
  const note=result.origin==='saved'?'这是已保存的真实结果，上方成本属于原运行。':'点击引用编号，可以核对支持这句话的原文。';
  const boundary=result.answer_status==='source_unavailable'?' 获取失败不代表论文未报告相关内容。':result.answer_status==='not_reviewed'?' 本次仅做引用结构检查。':'';
  $('answerNote').innerHTML=icon('info')+`<span>${escapeHTML(note+boundary)}</span>`;
  const usage=result.api_summary?.reported_usage||{}, prefix=result.origin==='saved'?'原运行':'本次';
  $('metrics').innerHTML=[{label:prefix+'模型请求',value:format(result.api_summary?.attempts),unit:'次'},{label:prefix+' Token',value:format(usage.total_tokens),unit:''},{label:prefix+'耗时',value:result.elapsed==null?'—':format(Math.round(result.elapsed*10)/10),unit:result.elapsed==null?'':'s'}].map(m=>`<div class="metric"><span>${m.label}</span><strong>${m.value}<small>${m.unit}</small></strong></div>`).join('');
  renderSources();renderActivity(result);showTab('answer');
}
async function loadExample(id) {
  if(state.busy||state.loading) return;
  const request=++state.exampleRequest; state.loading=true;syncControls();notice();
  try {
    const result=await api('/api/examples/'+id); if(request!==state.exampleRequest) return;
    $('question').value=result.query;renderResult(result);remember({example:id});
    window.scrollTo({top:0,behavior:'smooth'});
  } catch(error) { notice(error.message,true); }
  finally { if(request===state.exampleRequest) {state.loading=false;syncControls();} }
}
function home() {
  if(state.busy||state.loading) return;
  state.result=null;state.activeJob=null;document.body.classList.remove('reading','editing');$('questionBar').hidden=true;
  $('result').hidden=true;$('question').value='';notice();remember();
  window.scrollTo({top:0,behavior:'smooth'});$('question').focus({preventScroll:true});
}
function waiting() {
  state.busy=true;syncControls();compactQuestion();document.body.classList.add('reading');window.scrollTo({top:0,behavior:'smooth'});
  $('result').hidden=true;$('running').hidden=false;
}
async function pollJob(id) {
  clearTimeout(state.timer);
  try {
    const job=await api('/api/jobs/'+id);notice();
    if(job.status==='running') {
      $('elapsed').textContent=`${job.elapsed.toFixed(1)}s`;
      $('runningDescription').textContent=job.elapsed>45?'仍在处理。模型加载、CPU 重排或补查可能需要更长时间；无需再次发送。':'正在加载模型、检索原文并生成回答。复杂问题可能需要更长时间。';
      state.timer=setTimeout(()=>pollJob(id),1200);return;
    }
    state.busy=false;state.activeJob=null;syncControls();renderResult(job.result);remember({job:id});
    toast('结果已返回，可以查看答案与原文。');
  } catch(error) {
    if(error.status===404) {
      state.busy=false;state.activeJob=null;syncControls();$('running').hidden=true;remember();
      notice('当前服务已找不到这个任务，可能已重启。没有自动重新发送问题；已有运行文件仍保留。');
    } else notice(error.message+' 任务可能仍在运行。重新连接只读取状态，不会再次发送问题。',true);
  }
}
$('questionForm').addEventListener('submit',async(event)=>{
  event.preventDefault();if(state.busy||state.loading||!state.meta?.configured)return;
  const query=$('question').value.trim();if(!query){notice('先写下一个你想了解的问题。');$('question').focus();return;}
  // 请求发出前锁定，防止双击、快捷键或慢响应产生重复任务。
  notice();waiting();$('elapsed').textContent='0.0s';
  try {
    const job=await api('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,mode:state.mode,allow_network:$('network').checked})});
    state.activeJob=job.id;remember({job:job.id});pollJob(job.id);
  } catch(error) {
    state.busy=false;syncControls();$('running').hidden=true;
    notice(error.message+' 没有自动重发；若发送时断线，请先确认运行记录，避免重复调用。',true);
  }
});
document.addEventListener('click',(event)=>{
  const mode=event.target.closest('[data-mode]');if(mode&&!state.busy&&!state.loading){setMode(mode.dataset.mode);remember();}
  const example=event.target.closest('[data-example]');if(example)loadExample(example.dataset.example);
  const citation=event.target.closest('[data-citation]');
  if(citation){state.selected=Number(citation.dataset.citation);state.citedOnly=true;renderSources();document.querySelectorAll('.citation').forEach(el=>el.classList.toggle('selected',el.dataset.citation===citation.dataset.citation));const source=$('source-'+state.selected);if(source){if(window.matchMedia('(min-width:761px)').matches){const list=$('sources');list.scrollTo({top:list.scrollTop+source.getBoundingClientRect().top-list.getBoundingClientRect().top,behavior:'smooth'});}else source.scrollIntoView({behavior:'smooth',block:'nearest'});source.focus({preventScroll:true});}}
  const expand=event.target.closest('[data-expand]');if(expand){const card=$('source-'+expand.dataset.expand);const open=card.classList.toggle('expanded');expand.setAttribute('aria-expanded',open);expand.textContent=open?'收起原文 −':'展开原文 +';}
});
document.addEventListener('keydown',(event)=>{
  if((event.metaKey||event.ctrlKey)&&event.key==='Enter'&&!$('dialog').open){event.preventDefault();$('questionForm').requestSubmit();}
});
for(const name of ['answer','activity']) {
  $(name+'Tab').onclick=()=>showTab(name);
  $(name+'Tab').onkeydown=(event)=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const next=event.key==='Home'?'answer':event.key==='End'?'activity':name==='answer'?'activity':'answer';showTab(next);$(next+'Tab').focus();}};
}
$('citedButton').onclick=()=>{state.citedOnly=true;renderSources();};
$('allButton').onclick=()=>{state.citedOnly=false;renderSources();};
$('editQuestion').onclick=()=>{const editing=document.body.classList.toggle('editing');$('editQuestion').setAttribute('aria-expanded',editing);if(editing)$('question').focus();};
$('copyButton').onclick=async()=>{if(!state.result)return;try{await navigator.clipboard.writeText(state.result.answer+'\n\n引用编号为原始编号：\n'+state.result.citations.filter(c=>citedNumbers().has(c.number)).map(c=>`[${c.number}] ${c.title||c.source} · 第 ${c.page??'—'} 页`).join('\n'));toast('已复制完整答案');}catch{toast('浏览器未允许复制，可选中答案文本后复制。');}};
$('newQuestion').onclick=home;$('homeButton').onclick=home;
$('question').oninput=()=>remember();$('network').onchange=()=>remember();
$('closeDialog').onclick=()=>$('dialog').close();
$('dialog').addEventListener('close',()=>{const key=$('configKey');if(key)key.value='';});
$('dialog').onclick=(event)=>{if(event.target===$('dialog')){const rect=$('dialog').getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)$('dialog').close();}};
function openDialog(title,eyebrow,body){$('dialogTitle').textContent=title;$('dialogEyebrow').textContent=eyebrow;$('dialogBody').innerHTML=body;$('dialog').showModal();}
function libraryRows(filter='') {
  const papers=state.meta.papers.filter(p=>(p.title+' '+p.source).toLowerCase().includes(filter.toLowerCase()));
  $('libraryRows').innerHTML=papers.map(p=>`<div class="library-row"><span>${String(state.meta.papers.indexOf(p)+1).padStart(2,'0')}</span><div><h3>${escapeHTML(p.title)}</h3><p>${p.chunks} 段原文 · ${escapeHTML(p.source)}</p></div></div>`).join('')||'<p class="empty-sources">没有匹配的论文，试试标题中的其他关键词。</p>';
}
let importTimer;
function savedImport(){try{return localStorage.getItem('paperlens.import');}catch{return null;}}
async function watchImport(id){
  clearTimeout(importTimer);
  try{
    const job=await api('/api/imports/'+id);
    if($('importStatus'))$('importStatus').textContent=job.stage+(job.error?'：'+job.error:'')+(job.skipped?.length?'；跳过重复：'+job.skipped.join('、'):'');
    if(job.status==='running'){if($('uploadPapers'))$('uploadPapers').disabled=true;importTimer=setTimeout(()=>watchImport(id),1500);return;}
    if($('uploadPapers'))$('uploadPapers').disabled=false;
    if(job.status==='completed'){await init(false);if($('libraryRows'))libraryRows($('librarySearch').value);toast('论文库已更新');}
  }catch(error){if($('importStatus'))$('importStatus').textContent=error.message+' 可关闭后重新打开论文库查看状态。';if($('uploadPapers'))$('uploadPapers').disabled=false;}
}
$('libraryButton').onclick=()=>{
  if(!state.meta){notice('论文库尚未加载，请重新连接。',true);return;}
  openDialog('你的论文库','YOUR RESEARCH LIBRARY',`<form id="uploadForm" class="upload-form"><label for="paperFiles">添加论文 · PDF</label><input id="paperFiles" type="file" accept=".pdf,application/pdf" multiple required><label class="upload-columns"><input id="twoColumns" type="checkbox"> 本批论文按双栏顺序解析</label><p>每批最多5篇、共20MB；每篇最多200页。扫描件暂不支持OCR。成功入库后用于下一次提问。</p><button type="submit" id="uploadPapers" class="submit-button">添加并入库</button><p id="importStatus" role="status" aria-live="polite"></p></form><label class="sr-only" for="librarySearch">搜索论文标题</label><input id="librarySearch" class="library-search" placeholder="搜索论文标题…" type="search"><div id="libraryRows"></div>`);
  libraryRows();$('librarySearch').oninput=event=>libraryRows(event.target.value);
  const previous=savedImport();if(previous)watchImport(previous);
  $('uploadForm').onsubmit=async(event)=>{
    event.preventDefault();const files=Array.from($('paperFiles').files);const twoColumns=$('twoColumns').checked;
    if(!files.length||files.length>5||files.reduce((sum,f)=>sum+f.size,0)>20*1024*1024){$('importStatus').textContent='请选择1～5篇PDF，总大小不超过20MB。';return;}
    $('uploadPapers').disabled=true;$('importStatus').textContent='正在上传…';
    try{
      const encoded=await Promise.all(files.map(file=>new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve({name:file.name,data:String(reader.result).split(',')[1]});reader.onerror=()=>reject(new Error('读取文件失败。'));reader.readAsDataURL(file);}))); 
      const job=await api('/api/imports',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({files:encoded,two_columns:twoColumns})});
      try{localStorage.setItem('paperlens.import',job.id);}catch{}
      watchImport(job.id);
    }catch(error){if($('importStatus'))$('importStatus').textContent=error.message;if($('uploadPapers'))$('uploadPapers').disabled=false;}
  };
};
$('guideButton').onclick=()=>openDialog('在提问与原文之间。','A SMALL GUIDE','<div class="guide-copy"><h3>01 · 从问题开始</h3><p>写下你想理解、比较或核实的问题。Auto 先回答，再按缺口补查；RAG 使用固定本地流程；Agent 会逐项检查证据。</p><h3>02 · 顺着引用读下去</h3><p>答案中的编号连接到对应的论文原文和页码。可以展开片段，或切换全部证据。自动检查通过，不代表每个事实都已独立核验。</p><h3>03 · 看清回答的边界</h3><p>arXiv 默认关闭；开启后，Auto / Agent 可以获取外部原论文。获取失败不代表论文没有相关结论，页面会明确显示未核实状态。</p><h3>关于这间研究台</h3><p>历史案例回放不调用模型；实时提问会使用本地已配置的 API，并产生相应费用。本版同一时间处理一个问题，刷新可接续当前服务中的任务。服务重启后不自动重跑，运行文件保留在本地。</p></div>');
$('retryConnection').onclick=async()=>{if(state.activeJob){notice('正在重新连接…');pollJob(state.activeJob);}else await init(false);};
async function init(restore=true){
  try{
    state.meta=await api('/api/meta');$('paperCount').textContent=state.meta.papers.length;$('collectionSummary').textContent=`${state.meta.papers.length} 篇论文 · ${format(state.meta.chunks)} 段原文`;
    notice(state.meta.configured?'':'模型 API 尚未配置。可以先浏览真实案例与论文库。');
    if(restore){const saved=recall();$('question').value=saved.query||'';setMode(saved.mode||'auto');$('network').checked=state.mode!=='rag'&&saved.network===true;if(saved.job){state.activeJob=saved.job;waiting();pollJob(saved.job);}else if(saved.example)await loadExample(saved.example);}
    syncControls();
  }catch(error){notice(error.message,true);}
}
init();

$('configButton').onclick=async()=>{
  try {
    const config=await api('/api/config');
    openDialog('选择你的回答模型','MODEL SETTINGS',`<form id="configForm" class="config-form"><p>支持兼容 Chat Completions 的 API。配置保存在本机，保存后用于下一次提问。</p><label for="configBase">API 基础地址</label><input id="configBase" type="url" required placeholder="https://你的服务地址/v1" value="${escapeHTML(config.base_url)}"><label for="configKey">API Key · ${config.has_key?'已配置':'未配置'}</label><input id="configKey" type="password" autocomplete="new-password" ${config.key_source==='environment'?'disabled':''} placeholder="${config.key_source==='environment'?'由 RAG_API_KEY 环境变量提供':config.has_key?'留空保留现有密钥':'填写 API Key'}"><p class="config-help">密钥仅写入本机私有文件，不会回填或存入浏览器。${config.has_options?'已有高级调用参数会保留；切换服务商时需检查其兼容性。':''}</p><button type="button" class="fetch-models" id="fetchModels">获取模型</button><label for="modelSelect">选择模型</label><select id="modelSelect"><option value="">先获取模型列表</option></select><details id="manualModel"><summary>手动填写模型 ID（服务不支持列表时）</summary><label for="configModel">模型 ID</label><input id="configModel" maxlength="200" value="${escapeHTML(config.model)}"></details><p id="selectedModel">当前模型：${escapeHTML(config.model||'尚未选择')}</p><p id="configMessage" role="status"></p><button class="submit-button" id="saveConfig" type="submit">保存配置</button><p class="config-help">获取模型会携带密钥请求所填地址的 /models，不生成回答；保存后，下一次提问使用所选模型。</p></form>`);
    const currentForm=$('configForm');
    let modelRequest=0;
    const invalidateModels=()=>{modelRequest++;$('modelSelect').innerHTML='<option value="">配置已变化，请重新获取模型</option>';$('configModel').value='';$('selectedModel').textContent='尚未选择模型';};
    $('configBase').oninput=invalidateModels;$('configKey').oninput=invalidateModels;
    $('modelSelect').onchange=()=>{$('configModel').value=$('modelSelect').value;$('selectedModel').textContent='当前模型：'+($('modelSelect').value||'尚未选择');};
    $('configModel').oninput=()=>{$('modelSelect').value='';$('selectedModel').textContent='当前模型：'+$('configModel').value;};
    $('fetchModels').onclick=async()=>{
      const request=++modelRequest;$('fetchModels').disabled=true;$('saveConfig').disabled=true;$('configMessage').textContent='正在获取模型列表…';
      try{
        const result=await api('/api/models',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({base_url:$('configBase').value,api_key:$('configKey').value})});
        if(request!==modelRequest||!$('dialog').open||$('configForm')!==currentForm)return;
        $('modelSelect').innerHTML='<option value="">请选择模型</option>'+result.models.map(id=>`<option value="${escapeHTML(id)}">${escapeHTML(id)}</option>`).join('');
        if(result.models.includes($('configModel').value))$('modelSelect').value=$('configModel').value;
        $('configMessage').textContent=result.models.length?`已获取 ${result.models.length} 个模型，请选择后保存。列表由服务商返回，不代表每个模型都支持文本问答。`:'服务返回空列表，可手动填写模型 ID。';
      }catch(error){if(request===modelRequest&&$('configForm')===currentForm){$('configMessage').textContent=error.message;$('manualModel').open=true;}}
      finally{if($('configForm')===currentForm){$('fetchModels').disabled=false;$('saveConfig').disabled=false;}}
    };
    $('configForm').onsubmit=async(event)=>{
      event.preventDefault();if(!$('configModel').value.trim()){$('manualModel').open=true;$('configMessage').textContent='请选择一个模型，或手动填写模型 ID。';return;}$('saveConfig').disabled=true;
      const payload={base_url:$('configBase').value,model:$('configModel').value,api_key:$('configKey').value};
      try { await api('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});$('configKey').value='';await init(false);$('configMessage').textContent='已保存，下次提问生效。尚未发起模型请求。'; }
      catch(error){$('configMessage').textContent=error.message;}
      finally {payload.api_key='';$('saveConfig').disabled=false;}
    };
  }catch(error){notice(error.message,true);}
};
