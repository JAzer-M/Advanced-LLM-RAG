// PaperLens 前端：只调用本机 webui/server.py 已有接口；密钥不回填、不进入浏览器存储。
'use strict';

const $ = (id) => document.getElementById(id);
const escapeHTML = (text) => String(text ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// ---------- 界面文字（中 / 英）。后端生成的回答、错误详情保持原文。 ----------
const STRINGS = {
  zh: {
    'skip': '跳到主要内容', 'brand.aria': '回到研究台首页', 'nav.aria': '主导航', 'nav.ask': '研究台', 'nav.library': '论文库',
    'model.label': '模型', 'model.none': '未设置', 'lang.aria': '界面语言', 'help.aria': '使用说明',
    'home.title': '问一个关于这些论文的问题', 'home.lede': '回答里的每个编号都对应论文原文，可以逐条核对。',
    'home.library': '论文库', 'home.papers': '{n} 篇', 'home.addPapers': '添加论文',
    'home.examples': '已保存的回答', 'home.examplesNote': '打开时不调用模型',
    'example.transformer.title': 'Transformer 的前馈网络由什么组成？', 'example.transformer.tag': '本地论文回答',
    'example.flash.title': 'FlashAttention 如何减少显存读写？', 'example.flash.tag': '联网读取 arXiv 原论文后回答',
    'example.unavailable.title': '外部论文暂时无法获取时，会怎样？', 'example.unavailable.tag': '来源不可用时的交付',
    'composer.aria': '提问', 'composer.label': '问题', 'composer.placeholder': '例如：VGG 的 3×3 卷积层用多大的步长和填充？',
    'composer.hint': 'Enter 发送，Shift + Enter 换行', 'composer.submit': '提问', 'composer.resubmit': '重新提问',
    'composer.cancel': '取消', 'composer.busy': '正在回答…',
    'mode.aria': '回答方式',
    'mode.auto': 'Auto：先按固定流程回答；发现证据缺口、引用出错或无法回答时，再逐项补查。通常 2 次模型请求，最多 13 次。',
    'mode.auto.net': 'Auto：先按固定流程回答；发现证据缺口、引用出错或无法回答时，再逐项补查。通常 2 次模型请求，开启联网后最多 16 次。',
    'mode.rag': 'RAG：固定的检索与回答流程，只用本地论文，不能联网。通常 2 次模型请求。',
    'mode.agent': 'Agent：把问题拆成几个需求，逐项找证据后再回答。最多 11 次模型请求。',
    'mode.agent.net': 'Agent：把问题拆成几个需求，逐项找证据后再回答。开启联网后最多 14 次模型请求。',
    'net.label': '联网搜索', 'net.title': '目前只检索 arXiv 论文', 'net.ragOff': 'RAG 只使用本地论文，不能联网',
    'net.note': '联网搜索目前只查 arXiv：本地论文库里没有原论文时，按标题搜索一次、读取 1 篇 PDF。读到的内容只用于这次回答，不会加入论文库。',
    'notConfigured': '还没有设置模型服务。可以先看已保存的回答，或者打开模型设置。', 'notConfigured.action': '打开模型设置',
    'emptyLibrary': '论文库还是空的。先添加 PDF，入库完成后即可提问。', 'emptyLibrary.action': '添加论文',
    'offline': '无法连接本地服务，请确认启动 PaperLens 的终端窗口仍然开着。', 'offline.action': '重新连接',
    'result.edit': '修改问题', 'result.new': '新问题', 'answer.aria': '回答',
    'meta.replay': '已保存的回答，没有调用模型', 'meta.autoDirect': 'Auto 直接回答', 'meta.autoAgent': 'Auto 升级为 Agent',
    'meta.web': '联网读取 {n} 篇 arXiv 论文', 'meta.requests': '{n} 次模型请求', 'meta.requestsFailed': '{n} 次模型请求，{f} 次失败',
    'meta.tokens': '{n} token', 'meta.seconds': '{n} 秒',
    'answer.copy': '复制回答', 'answer.copied': '已复制回答', 'answer.copyFailed': '浏览器不允许复制，请选中文字后手动复制。',
    'answer.copySources': '引用（原始编号）：', 'answer.page': '第 {p} 页',
    'cite.aria': '查看原文 {n}', 'cite.title': '原始编号 {n}',
    'disclaimer.checked': '引用编号和原文位置已自动检查；内容是否成立，请对照右侧原文判断。',
    'disclaimer.reviewed': '模型已逐项复核这份回答；复核不等于独立核实，请对照右侧原文判断。',
    'disclaimer.other': '自动检查不等于独立核实，请对照右侧原文判断。',
    'banner.insufficient': '证据不足：回答说明了缺口，没能补全的部分还没有核实。',
    'banner.unavailable': '外部论文暂时无法获取，相关内容没有核实。获取失败不代表论文没有报告这些内容。',
    'banner.degraded': '只完成了一部分：保留的是引用格式检查通过的初稿，事实没有经过完整复核。',
    'banner.reviewFailed': '回答没有通过复核，请特别留意右侧原文。',
    'banner.citationFailed': '引用检查没有通过，部分编号可能对不上原文。',
    'details.title': '运行详情', 'details.route': '执行路径', 'details.stop': '停止原因', 'details.passages': '原文',
    'details.passagesValue': '取得 {n} 段，回答引用了其中 {m} 段', 'details.external': '，{k} 段来自 arXiv',
    'details.coverage': '本地需求', 'details.coverageValue': '本地检查支持 {a}/{b} 项（不含联网补到的证据）',
    'details.actions': '工具行动', 'details.web': '联网', 'details.webOff': '未开启',
    'details.webValue': 'arXiv 请求 {n} 次，读取 {k} 篇论文', 'details.requests': '模型请求',
    'details.requestsValue': '{n} 次，失败 {f} 次，自动重试 {r} 次', 'details.tokens': 'Token',
    'details.tokensValue': '输入 {i}，输出 {o}', 'details.answer': '回答状态', 'details.library': '论文库',
    'details.libraryValue': '{n} 篇，{c} 段', 'details.date': '保存日期',
    'route.direct': 'RAG 先回答后没有发现证据缺口，没有升级为 Agent。',
    'route.escalated': 'RAG 先回答后发现缺口，升级为 Agent 逐项补查。',
    'route.rag': '固定的检索与回答流程。', 'route.agent': '逐项检查需求、补查证据后回答。',
    'tool.search': '检索本地论文', 'tool.read_neighbors': '读取相邻原文', 'tool.search_arxiv': '搜索 arXiv',
    'tool.read_arxiv_paper': '读取 arXiv PDF', 'tool.completed': '完成', 'tool.failed': '失败',
    'status.review_passed': '复核通过', 'status.not_reviewed': '只做了引用检查', 'status.insufficient_evidence': '证据不足',
    'status.source_unavailable': '外部来源不可用', 'status.review_failed': '复核未通过', 'status.citation_failed': '引用检查未通过',
    'status.unavailable': '没有可交付的回答',
    'stop.rag_first_direct': 'RAG 先答已满足，没有升级补查', 'stop.rag_answer': '固定流程完成', 'stop.model_stop': 'Agent 判断证据已经足够',
    'stop.external_timeout': '外部请求超时，没有自动重试', 'stop.external_rate_limited': '外部服务限流，没有自动重试',
    'stop.external_http_error': '外部请求出错，没有自动重试', 'stop.external_transport_error': '外部连接失败，没有自动重试',
    'stop.action_budget': '工具行动达到上限', 'stop.api_budget': '模型请求达到上限', 'stop.processing_failed': '处理中途出错',
    'stop.worker_failed': '问答进程没有完成',
    'web.not_requested': '未开启', 'web.completed': '完成', 'web.failed': '失败', 'web.skipped': '没有需要联网的缺口',
    'sources.title': '原文', 'sources.cited': '回答引用了 {m} 段', 'sources.citedWeb': '回答引用了 {m} 段，其中 {k} 段来自联网读取的论文',
    'sources.more': '显示另外 {n} 段检索到但没有引用的原文', 'sources.less': '只看被引用的原文',
    'sources.none': '这次没有可以核对的原文段落。', 'sources.waiting': '回答完成后，这里会列出引用的原文。',
    'sources.page': '第 {p} 页', 'sources.noPage': '页码未知', 'sources.openPdf': '打开 PDF',
    'running.title': '正在检索原文并生成回答', 'running.elapsed': '已用 {n} 秒',
    'running.hint': '通常需要 15 到 60 秒，联网或补查时会更久。不需要重复发送。',
    'running.slow': '还在处理。加载模型、重排或补查可能更久，问题不会被重复发送。',
    'failed.title': '没有拿到回答', 'failed.hint': '可能是模型服务没有启动、地址或密钥有误，或者网络中断。运行记录已保存在本机。',
    'failed.service': '当前模型服务：{url}', 'failed.settings': '检查模型设置', 'failed.retry': '重新提问',
    'lost.title': '找不到刚才的任务', 'lost.body': '本地服务重启过，刚才的任务无法接着显示。问题没有重新发送，运行记录仍保存在本机的 logs/webui 文件夹。',
    'sendFailed': '问题没有发出去：{msg} 没有自动重发。',
    'pollFailed': '暂时读不到任务状态：{msg} 任务可能还在运行，重新连接只读取状态，不会重发问题。',
    'empty': '先写下你想问的问题。', 'toast.done': '回答已完成',
    'library.title': '论文库', 'library.lede': '{n} 篇论文，{c} 段原文。新加入的论文会用于下一次提问。',
    'library.add': '添加论文', 'library.choose': '选择 PDF', 'library.noFiles': '还没有选择文件', 'library.files': '已选择 {n} 个文件',
    'library.twoCol': '按双栏版式解析', 'library.limits': '每次 1 到 5 篇 PDF，合计不超过 20 MB，每篇不超过 200 页。扫描件暂不支持。',
    'library.submit': '添加并入库', 'library.uploading': '正在上传…', 'library.badFiles': '请选择 1 到 5 篇 PDF，合计不超过 20 MB。',
    'library.done': '论文库已更新', 'library.skipped': '已跳过重复的文件：{list}', 'library.search': '搜索论文标题',
    'library.passages': '{n} 段原文', 'library.empty': '没有找到匹配的论文。',
    'settings.title': '模型设置', 'settings.base': '服务地址', 'settings.keySaved': '已保存', 'settings.keyMissing': '未填写',
    'settings.keyEnv': '来自环境变量', 'settings.keyKeep': '留空则继续使用已保存的密钥', 'settings.keyNew': '填写 API Key',
    'settings.keyEnvPh': '由 RAG_API_KEY 环境变量提供', 'settings.keyNeeded': '服务地址改了，请填写这个地址对应的 API Key。',
    'settings.model': '模型', 'settings.showList': '显示模型列表', 'settings.fetch': '获取列表', 'settings.fetching': '获取中…',
    'settings.fetched': '已获取 {n} 个模型，可以从列表里选。', 'settings.fetchedEmpty': '服务返回了空列表，可以直接输入模型名。',
    'settings.noMatch': '没有匹配的模型',
    'settings.modelHelp': '正在使用 {m}。可以直接输入模型名，也可以先获取列表再选。',
    'settings.modelHelpNone': '还没有选择模型。可以直接输入模型名，也可以先获取列表再选。',
    'settings.options': '原有的高级调用参数会继续使用，换了服务或模型后请确认它们仍然兼容。',
    'settings.privacy': '密钥只保存在这台电脑上，不会进入浏览器。', 'settings.cancel': '取消', 'settings.save': '保存',
    'settings.saving': '保存中…', 'settings.saved': '已保存，下次提问生效', 'settings.needModel': '请填写或选择一个模型。',
    'settings.close': '关闭',
    'help.title': '使用说明',
    'help.body': [
      ['怎么提问', '用中文或英文写下想核实、比较或理解的问题，按 Enter 发送。回答完成后，答案里的每个编号都能点开，右侧会标出对应的论文原文。'],
      ['三种回答方式', 'Auto 先按固定流程回答，发现缺口时再补查，适合大多数问题。RAG 只走固定流程，最快。Agent 把问题拆成几项逐一找证据，最慢也最细。'],
      ['联网搜索', '目前只查 arXiv：本地论文库里没有原论文时，按标题搜索一次、读取一篇 PDF。读到的内容只用于这次回答，不会加入论文库。RAG 不能联网。'],
      ['怎么看待回答', '引用检查和模型复核都不等于独立核实。重要结论请对照右侧原文。外部论文获取失败时，页面会明确说明哪些内容没有核实。'],
      ['费用', '打开已保存的回答不调用模型。每次实时提问会使用你在模型设置里配置的服务，并按它的规则计费。同一时间只处理一个问题。'],
    ],
  },
  en: {
    'skip': 'Skip to main content', 'brand.aria': 'Back to the PaperLens home page', 'nav.aria': 'Main', 'nav.ask': 'Ask', 'nav.library': 'Library',
    'model.label': 'Model', 'model.none': 'Not set', 'lang.aria': 'Interface language', 'help.aria': 'How it works',
    'home.title': 'Ask a question about these papers', 'home.lede': 'Every number in an answer links to the original passage, so you can check each claim.',
    'home.library': 'Library', 'home.papers': '{n} papers', 'home.addPapers': 'Add papers',
    'home.examples': 'Saved answers', 'home.examplesNote': 'Opening one doesn’t call the model',
    'example.transformer.title': 'What makes up the Transformer’s feed-forward network?', 'example.transformer.tag': 'Answered from local papers',
    'example.flash.title': 'How does FlashAttention reduce memory reads and writes?', 'example.flash.tag': 'Answered after reading the arXiv paper',
    'example.unavailable.title': 'What happens when an external paper can’t be fetched?', 'example.unavailable.tag': 'What you get when the source is unavailable',
    'composer.aria': 'Ask', 'composer.label': 'Question', 'composer.placeholder': 'For example: what stride and padding does VGG use for its 3×3 convolutions?',
    'composer.hint': 'Enter to send, Shift + Enter for a new line', 'composer.submit': 'Ask', 'composer.resubmit': 'Ask again',
    'composer.cancel': 'Cancel', 'composer.busy': 'Answering…',
    'mode.aria': 'Answer mode',
    'mode.auto': 'Auto answers with the fixed pipeline first and checks each requirement only when it finds a gap, a citation error, or can’t answer. Usually 2 model requests, at most 13.',
    'mode.auto.net': 'Auto answers with the fixed pipeline first and checks each requirement only when it finds a gap, a citation error, or can’t answer. Usually 2 model requests, at most 16 with web search on.',
    'mode.rag': 'RAG runs the fixed retrieve-and-answer pipeline on local papers only, without the web. Usually 2 model requests.',
    'mode.agent': 'Agent splits the question into requirements and finds evidence for each before answering. At most 11 model requests.',
    'mode.agent.net': 'Agent splits the question into requirements and finds evidence for each before answering. At most 14 model requests with web search on.',
    'net.label': 'Web search', 'net.title': 'Currently searches arXiv papers only', 'net.ragOff': 'RAG uses local papers only',
    'net.note': 'Web search currently covers arXiv only: when the original paper isn’t in your library, it searches by title once and reads one PDF. What it reads is used for this answer only and isn’t added to your library.',
    'notConfigured': 'No model service is set up yet. You can open a saved answer, or set up a model.', 'notConfigured.action': 'Open model settings',
    'emptyLibrary': 'Your library is empty. Add a PDF and wait for import to finish before asking a question.', 'emptyLibrary.action': 'Add papers',
    'offline': 'Can’t reach the local service. Make sure the terminal window running PaperLens is still open.', 'offline.action': 'Reconnect',
    'result.edit': 'Edit question', 'result.new': 'New question', 'answer.aria': 'Answer',
    'meta.replay': 'Saved answer, no model call', 'meta.autoDirect': 'Auto, answered directly', 'meta.autoAgent': 'Auto, escalated to Agent',
    'meta.web': 'Read {n} arXiv paper(s)', 'meta.requests': '{n} model requests', 'meta.requestsFailed': '{n} model requests, {f} failed',
    'meta.tokens': '{n} tokens', 'meta.seconds': '{n} s',
    'answer.copy': 'Copy answer', 'answer.copied': 'Answer copied', 'answer.copyFailed': 'The browser blocked copying. Select the text and copy it manually.',
    'answer.copySources': 'Citations (original numbers):', 'answer.page': 'p. {p}',
    'cite.aria': 'Show passage {n}', 'cite.title': 'Original number {n}',
    'disclaimer.checked': 'Citation numbers and passage locations were checked automatically. Compare with the passages to judge whether the content holds.',
    'disclaimer.reviewed': 'The model reviewed this answer point by point. That isn’t independent verification, so compare with the passages.',
    'disclaimer.other': 'Automatic checks aren’t independent verification. Compare with the passages.',
    'banner.insufficient': 'Not enough evidence: the answer names the gaps, and the parts it couldn’t fill aren’t verified.',
    'banner.unavailable': 'The external paper couldn’t be fetched, so related content isn’t verified. A failed fetch doesn’t mean the paper doesn’t report it.',
    'banner.degraded': 'Partly finished: this is the first draft that passed the citation format check; its facts weren’t fully reviewed.',
    'banner.reviewFailed': 'The answer didn’t pass review. Check it carefully against the passages.',
    'banner.citationFailed': 'The citation check failed; some numbers may not match the passages.',
    'details.title': 'Run details', 'details.route': 'Path', 'details.stop': 'Stopped because', 'details.passages': 'Passages',
    'details.passagesValue': '{n} retrieved, {m} cited', 'details.external': ', {k} from arXiv',
    'details.coverage': 'Requirements', 'details.coverageValue': '{a} of {b} supported by the local check (excluding web evidence)',
    'details.actions': 'Tool actions', 'details.web': 'Web', 'details.webOff': 'Off',
    'details.webValue': '{n} arXiv requests, {k} paper(s) read', 'details.requests': 'Model requests',
    'details.requestsValue': '{n} sent, {f} failed, {r} automatic retries', 'details.tokens': 'Tokens',
    'details.tokensValue': '{i} input, {o} output', 'details.answer': 'Answer status', 'details.library': 'Library',
    'details.libraryValue': '{n} papers, {c} passages', 'details.date': 'Saved on',
    'route.direct': 'RAG answered first and found no evidence gap, so it didn’t escalate to Agent.',
    'route.escalated': 'RAG answered first, found a gap, and escalated to Agent.',
    'route.rag': 'The fixed retrieve-and-answer pipeline.', 'route.agent': 'Checked each requirement and gathered evidence before answering.',
    'tool.search': 'Search local papers', 'tool.read_neighbors': 'Read neighboring passages', 'tool.search_arxiv': 'Search arXiv',
    'tool.read_arxiv_paper': 'Read arXiv PDF', 'tool.completed': 'done', 'tool.failed': 'failed',
    'status.review_passed': 'Passed review', 'status.not_reviewed': 'Citation check only', 'status.insufficient_evidence': 'Not enough evidence',
    'status.source_unavailable': 'Source unavailable', 'status.review_failed': 'Failed review', 'status.citation_failed': 'Citation check failed',
    'status.unavailable': 'No answer',
    'stop.rag_first_direct': 'RAG answer was enough, no escalation', 'stop.rag_answer': 'Fixed pipeline finished', 'stop.model_stop': 'Agent judged the evidence sufficient',
    'stop.external_timeout': 'External request timed out, not retried', 'stop.external_rate_limited': 'External service rate-limited, not retried',
    'stop.external_http_error': 'External request failed, not retried', 'stop.external_transport_error': 'External connection failed, not retried',
    'stop.action_budget': 'Tool action limit reached', 'stop.api_budget': 'Model request limit reached', 'stop.processing_failed': 'Processing failed midway',
    'stop.worker_failed': 'The answering process didn’t finish',
    'web.not_requested': 'Off', 'web.completed': 'Done', 'web.failed': 'Failed', 'web.skipped': 'No gap needed the web',
    'sources.title': 'Passages', 'sources.cited': '{m} cited in the answer', 'sources.citedWeb': '{m} cited, {k} from papers read on the web',
    'sources.more': 'Show {n} more passages that were retrieved but not cited', 'sources.less': 'Show cited passages only',
    'sources.none': 'There are no passages to check for this answer.', 'sources.waiting': 'Cited passages will appear here when the answer is ready.',
    'sources.page': 'p. {p}', 'sources.noPage': 'Page unknown', 'sources.openPdf': 'Open PDF',
    'running.title': 'Finding passages and writing the answer', 'running.elapsed': '{n} s elapsed',
    'running.hint': 'This usually takes 15 to 60 seconds, longer with web search or extra checks. No need to send it again.',
    'running.slow': 'Still working. Loading models, reranking or extra checks can take longer; the question won’t be sent twice.',
    'failed.title': 'No answer this time', 'failed.hint': 'The model service may not be running, the address or key may be wrong, or the network dropped. The run log is saved on this computer.',
    'failed.service': 'Current model service: {url}', 'failed.settings': 'Check model settings', 'failed.retry': 'Ask again',
    'lost.title': 'Can’t find the last task', 'lost.body': 'The local service restarted, so the last task can’t be resumed. The question wasn’t sent again, and its log is still in the logs/webui folder.',
    'sendFailed': 'The question wasn’t sent: {msg} Nothing was resent.',
    'pollFailed': 'Can’t read the task status: {msg} It may still be running; reconnecting only reads the status and won’t resend.',
    'empty': 'Type a question first.', 'toast.done': 'Answer ready',
    'library.title': 'Library', 'library.lede': '{n} papers, {c} passages. Papers you add are used from your next question.',
    'library.add': 'Add papers', 'library.choose': 'Choose PDFs', 'library.noFiles': 'No files chosen', 'library.files': '{n} files chosen',
    'library.twoCol': 'Parse as a two-column layout', 'library.limits': '1 to 5 PDFs at a time, up to 20 MB in total and 200 pages each. Scanned PDFs aren’t supported yet.',
    'library.submit': 'Add to library', 'library.uploading': 'Uploading…', 'library.badFiles': 'Choose 1 to 5 PDFs, up to 20 MB in total.',
    'library.done': 'Library updated', 'library.skipped': 'Skipped duplicates: {list}', 'library.search': 'Search paper titles',
    'library.passages': '{n} passages', 'library.empty': 'No matching papers.',
    'settings.title': 'Model settings', 'settings.base': 'Service address', 'settings.keySaved': 'Saved', 'settings.keyMissing': 'Not set',
    'settings.keyEnv': 'From environment', 'settings.keyKeep': 'Leave blank to keep the saved key', 'settings.keyNew': 'Enter an API key',
    'settings.keyEnvPh': 'Provided by the RAG_API_KEY environment variable', 'settings.keyNeeded': 'The address changed. Enter the API key for this address.',
    'settings.model': 'Model', 'settings.showList': 'Show model list', 'settings.fetch': 'Get list', 'settings.fetching': 'Getting…',
    'settings.fetched': '{n} models found. Pick one from the list.', 'settings.fetchedEmpty': 'The service returned an empty list. Type a model name instead.',
    'settings.noMatch': 'No matching models',
    'settings.modelHelp': 'Using {m}. Type a model name, or get the list and pick one.',
    'settings.modelHelpNone': 'No model chosen yet. Type a model name, or get the list and pick one.',
    'settings.options': 'Your existing advanced call options stay in use. After changing the service or model, make sure they still work.',
    'settings.privacy': 'The key is stored only on this computer and never sent to the browser.', 'settings.cancel': 'Cancel', 'settings.save': 'Save',
    'settings.saving': 'Saving…', 'settings.saved': 'Saved. Used from your next question.', 'settings.needModel': 'Enter or choose a model.',
    'settings.close': 'Close',
    'help.title': 'How it works',
    'help.body': [
      ['Asking', 'Write the question you want to check, compare or understand, in English or Chinese, and press Enter. When the answer is ready, click any number in it to see the matching passage on the right.'],
      ['Answer modes', 'Auto answers with the fixed pipeline and checks further only when it finds a gap; it suits most questions. RAG runs only the fixed pipeline and is fastest. Agent breaks the question into parts and finds evidence for each; slowest and most thorough.'],
      ['Web search', 'It currently covers arXiv only: when the original paper isn’t in your library, it searches by title once and reads one PDF. What it reads is used for that answer only and isn’t added to your library. RAG can’t use the web.'],
      ['Reading an answer', 'Citation checks and model review aren’t independent verification. Check important claims against the passages. If an external paper can’t be fetched, the page says which content isn’t verified.'],
      ['Cost', 'Opening a saved answer doesn’t call the model. Each live question uses the service in Model settings and is billed by its rules. One question is handled at a time.'],
    ],
  },
};

let lang = 'zh';
try { if (localStorage.getItem('paperlens.lang') === 'en') lang = 'en'; } catch {}
const t = (key, vars = {}) => {
  const value = STRINGS[lang][key] ?? STRINGS.zh[key] ?? key;
  return typeof value === 'string' ? value.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '') : value;
};
const number = (n) => n == null ? '—' : Number(n).toLocaleString(lang === 'en' ? 'en-US' : 'zh-CN');
const seconds = (n) => n == null ? null : (Math.round(n * 10) / 10).toFixed(1);

// ---------- 状态 ----------
const state = {
  view: 'ask', mode: 'auto', net: false, meta: null, config: null,
  result: null, busy: false, loading: false, job: null, timer: null, exampleRequest: 0,
  editing: false, sel: null, showUncited: false, lost: false, composing: false,
};
const SESSION = 'paperlens.webui.session';
function remember(extra = {}) {
  try { sessionStorage.setItem(SESSION, JSON.stringify({ query: $('question').value, mode: state.mode, net: state.net, ...extra })); } catch {}
}
function recall() { try { return JSON.parse(sessionStorage.getItem(SESSION) || '{}'); } catch { return {}; } }

// ---------- 通用 ----------
async function api(path, options = {}) {
  let response;
  try { response = await fetch(path, { ...options, signal: AbortSignal.timeout(15000) }); }
  catch { const error = new Error(t('offline')); error.offline = true; throw error; }
  let value = {};
  try { value = await response.json(); } catch {}
  if (state.offline) { state.offline = false; notice(''); }
  if (!response.ok) { const error = new Error(value.error || response.statusText); error.status = response.status; throw error; }
  return value;
}
const postJSON = (path, body) => api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

function notice(message, action = null) {
  $('notice').hidden = !message;
  $('noticeText').textContent = message || '';
  $('noticeAction').hidden = !action;
  if (action) { $('noticeAction').textContent = action.label; $('noticeAction').onclick = action.run; }
}
function offline() {
  state.offline = true;
  notice(t('offline'), { label: t('offline.action'), run: () => reconnect() });
}
function toast(message) {
  $('toast').textContent = message; $('toast').hidden = false;
  clearTimeout(state.toastTimer); state.toastTimer = setTimeout(() => { $('toast').hidden = true; }, 2600);
}

// ---------- 语言 ----------
function applyLanguage() {
  document.documentElement.lang = lang === 'en' ? 'en' : 'zh-CN';
  document.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll('[data-i18n-aria]').forEach((el) => el.setAttribute('aria-label', t(el.dataset.i18nAria)));
  document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => el.setAttribute('placeholder', t(el.dataset.i18nPlaceholder)));
  document.querySelectorAll('[data-i18n-title]').forEach((el) => el.setAttribute('title', t(el.dataset.i18nTitle)));
  document.querySelectorAll('[data-lang]').forEach((el) => el.setAttribute('aria-pressed', String(el.dataset.lang === lang)));
  $('helpBody').innerHTML = t('help.body').map(([h, p]) => `<h3>${escapeHTML(h)}</h3><p>${escapeHTML(p)}</p>`).join('');
  renderMeta(); syncControls(); renderHome(); renderLibrary();
  if (state.result) renderResult(state.result, false);
  else if (state.busy) renderRunning(state.elapsed || 0);
  else if (state.lost) showLost();
  if ($('settingsDialog').open) refreshSettingsText();
}

// ---------- 视图 ----------
function showView(view) {
  const changed = state.view !== view;
  state.view = view;
  $('askView').hidden = view !== 'ask';
  $('libraryView').hidden = view !== 'library';
  document.querySelectorAll('[data-view]').forEach((el) => {
    if (el.dataset.view === view) el.setAttribute('aria-current', 'page'); else el.removeAttribute('aria-current');
  });
  if (view === 'library') renderLibrary();
  if (changed) window.scrollTo({ top: 0 });
}
const sep = () => (lang === 'en' ? ', ' : '，');
const colon = () => (lang === 'en' ? ': ' : '：');
function reading(on) {
  $('home').hidden = on; $('reading').hidden = !on;
}
function placeComposer() {
  const slot = state.editing ? $('editSlot') : $('homeSlot');
  const pieces = [$('composer'), $('modeHint'), $('netNote')];
  pieces.forEach((el) => slot.appendChild(el));
  $('cancelEdit').hidden = !state.editing;
  $('editButton').setAttribute('aria-expanded', String(state.editing));
  syncControls();
}
function home() {
  if (state.busy || state.loading) return;
  state.result = null; state.job = null; state.lost = false; state.editing = false; state.sel = null;
  $('question').value = ''; placeComposer(); reading(false); showView('ask'); remember();
  $('question').focus({ preventScroll: true });
}

// ---------- 输入区 ----------
function syncControls() {
  const locked = state.busy || state.loading;
  const configured = !!state.meta?.configured;
  $('question').disabled = locked;
  $('submitButton').disabled = locked || !configured || !state.meta?.chunks;
  $('submitButton').textContent = state.busy ? t('composer.busy') : state.editing ? t('composer.resubmit') : t('composer.submit');
  document.querySelectorAll('[data-mode]').forEach((el) => {
    el.setAttribute('aria-pressed', String(el.dataset.mode === state.mode)); el.disabled = locked;
  });
  const netAllowed = state.mode !== 'rag';
  if (!netAllowed) state.net = false;
  $('netSwitch').setAttribute('aria-checked', String(state.net));
  $('netSwitch').disabled = locked || !netAllowed;
  $('netSwitch').title = netAllowed ? t('net.title') : t('net.ragOff');
  $('netSwitch').setAttribute('aria-label', t('net.label'));
  $('modeHint').textContent = t(state.mode === 'rag' ? 'mode.rag' : `mode.${state.mode}${state.net ? '.net' : ''}`);
  $('netNote').hidden = !state.net;
  $('netNote').textContent = t('net.note');
  ['editButton', 'newButton', 'cancelEdit', 'brandButton'].forEach((id) => { $(id).disabled = locked; });
  document.querySelectorAll('.example').forEach((el) => { el.disabled = locked; });
}
function renderMeta() {
  const meta = state.meta;
  $('paperCount').textContent = meta ? meta.papers.length : '—';
  const unset = !meta?.model;
  $('modelName').textContent = unset ? t('model.none') : meta.model;
  $('modelButton').classList.toggle('unset', unset);
  $('modelButton').title = unset ? '' : meta.model;
  if (meta && !meta.chunks && !state.offline) {
    notice(t('emptyLibrary'), { label: t('emptyLibrary.action'), run: () => showView('library') });
  } else if (meta && !meta.configured && !state.offline) {
    notice(t('notConfigured'), { label: t('notConfigured.action'), run: openSettings });
  } else if (!state.offline) notice('');
}
function renderHome() {
  const meta = state.meta; if (!meta) return;
  $('homePaperCount').textContent = t('home.papers', { n: meta.papers.length });
  $('homePapers').innerHTML = meta.papers.map((p) => `<li>${escapeHTML(p.title || p.source)}</li>`).join('');
  $('examples').innerHTML = (meta.examples || []).map((ex) => {
    const known = STRINGS.zh[`example.${ex.id}.title`];
    const title = known ? t(`example.${ex.id}.title`) : ex.title;
    const tag = known ? t(`example.${ex.id}.tag`) : ex.tag;
    return `<button type="button" class="example" data-example="${escapeHTML(ex.id)}"><strong>${escapeHTML(title)}</strong><span>${escapeHTML(tag)}</span></button>`;
  }).join('');
  syncControls();
}

// Enter 发送；输入法选词时的 Enter 不发送（Safari 先触发 compositionend，所以同时检查 keyCode 229）。
$('question').addEventListener('compositionstart', () => { state.composing = true; });
$('question').addEventListener('compositionend', () => { state.composing = false; state.composedAt = Date.now(); });
$('question').addEventListener('keydown', (event) => {
  if (event.key !== 'Enter' || event.shiftKey || event.altKey) return;
  if (event.isComposing || event.keyCode === 229 || state.composing || Date.now() - (state.composedAt || 0) < 30) return;
  event.preventDefault();
  $('composer').requestSubmit();
});
$('question').addEventListener('input', () => remember());

document.querySelectorAll('[data-mode]').forEach((el) => el.addEventListener('click', () => {
  state.mode = el.dataset.mode; syncControls(); remember();
}));
$('netSwitch').addEventListener('click', () => {
  if (state.mode === 'rag') return;
  state.net = !state.net; syncControls(); remember();
});
$('cancelEdit').addEventListener('click', () => {
  state.editing = false; $('question').value = state.result?.query || ''; placeComposer();
});
$('editButton').addEventListener('click', () => {
  state.editing = !state.editing;
  if (state.editing && state.result) $('question').value = state.result.query;
  placeComposer();
  if (state.editing) $('question').focus();
});
$('newButton').addEventListener('click', home);
$('brandButton').addEventListener('click', () => { if (state.view !== 'ask') showView('ask'); else home(); });

$('composer').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (state.busy || state.loading || !state.meta?.configured || !state.meta?.chunks) return;
  const query = $('question').value.trim();
  if (!query) { notice(t('empty')); $('question').focus(); return; }
  notice('');
  // 请求发出前就锁定，避免双击或回车重复提交。
  state.busy = true; state.editing = false; state.result = null; state.lost = false; state.sel = null;
  placeComposer(); reading(true); renderRunning(0, query);
  try {
    const job = await postJSON('/api/run', { query, mode: state.mode, allow_network: state.net });
    state.job = job.id; remember({ job: job.id }); poll(job.id);
  } catch (error) {
    state.busy = false; syncControls();
    if (error.offline) offline();
    else notice(t('sendFailed', { msg: error.message }));
    state.editing = true; placeComposer(); renderRunning(null, query, true);
  }
});

// ---------- 运行中 ----------
function renderRunning(elapsed, query, stopped = false) {
  state.elapsed = elapsed;
  $('sourcesPanel').hidden = false;
  if (query != null) $('resultQuestion').textContent = query;
  $('resultMeta').innerHTML = ''; $('statusBanner').hidden = true;
  $('answerView').hidden = true; $('problemView').hidden = true;
  $('runningView').hidden = stopped;
  if (!stopped) {
    $('runningTime').textContent = t('running.elapsed', { n: seconds(elapsed || 0) });
    $('runningHint').textContent = elapsed > 45 ? t('running.slow') : t('running.hint');
  }
  $('sources').innerHTML = `<p class="sources-empty">${escapeHTML(t('sources.waiting'))}</p>`;
  $('sourcesCount').textContent = ''; $('moreSources').hidden = true;
}
async function poll(id) {
  clearTimeout(state.timer);
  try {
    const job = await api('/api/jobs/' + id);
    if (job.status === 'running') {
      renderRunning(job.elapsed);
      state.timer = setTimeout(() => poll(id), 1200);
      return;
    }
    state.busy = false; state.job = null; syncControls();
    renderResult(job.result); remember({ job: id });
    toast(t('toast.done'));
  } catch (error) {
    if (error.status === 404) {
      state.busy = false; state.job = null; syncControls(); remember();
      showLost();
    } else if (error.offline) {
      offline();
      state.timer = setTimeout(() => poll(id), 4000);
    } else {
      notice(t('pollFailed', { msg: error.message }), { label: t('offline.action'), run: () => { notice(''); poll(id); } });
    }
  }
}

// ---------- 引用编号与回答 ----------
function citationIndex(result) {
  const valid = new Map(result.citations.map((c) => [c.number, c]));
  const cited = [];
  for (const m of result.answer.matchAll(/\[(\d+)\]/g)) {
    const n = Number(m[1]);
    if (valid.has(n) && !cited.includes(n)) cited.push(n);
  }
  const order = [...cited, ...result.citations.map((c) => c.number).filter((n) => !cited.includes(n))];
  const display = new Map(order.map((n, i) => [n, i + 1]));
  return { valid, cited, display };
}
function formatText(text) {
  return escapeHTML(text).replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
}
function citeButton(n) {
  const d = state.index.display.get(n);
  return `<button type="button" class="cite" data-n="${n}" aria-label="${escapeHTML(t('cite.aria', { n: d }))}" title="${escapeHTML(t('cite.title', { n }))}">${d}</button>`;
}
// 把“说法 + 紧随的引用编号”包在一起：点编号时，回答里的这句话和右侧原文同时标出。
function citedText(text) {
  const tokens = String(text).split(/((?:\s*\[\d+\])+)/);
  let html = '';
  for (let i = 0; i < tokens.length; i += 2) {
    let piece = tokens[i] ?? '';
    const run = tokens[i + 1];
    if (run == null) { html += formatText(piece); break; }
    const nums = [...run.matchAll(/\[(\d+)\]/g)].map((m) => Number(m[1]));
    const valid = nums.filter((n) => state.index.valid.has(n));
    if (!valid.length) { html += formatText(piece + run); continue; }
    let cut = -1;
    const boundary = /[。；！？;!?：\n]|[.:](?=\s)/g;
    let m; while ((m = boundary.exec(piece))) cut = m.index;
    let prefix = piece.slice(0, cut + 1), claim = piece.slice(cut + 1);
    const lead = claim.match(/^[\s，,、]*/)[0];
    prefix += lead; claim = claim.slice(lead.length);
    const trail = claim.match(/\s*$/)[0];
    claim = claim.slice(0, claim.length - trail.length);
    html += formatText(prefix);
    if (claim) html += `<span class="claim" data-cites="${valid.join(' ')}">${formatText(claim)}</span>`;
    let chips = valid.map(citeButton).join('');
    const next = tokens[i + 2];
    if (next && /^[。，；：！？、,.;:!?）)]/.test(next)) { chips += escapeHTML(next[0]); tokens[i + 2] = next.slice(1); }
    html += '⁠' + `<span class="cites">${chips}</span>`;
  }
  return html;
}
function inline(text) {
  return String(text).split(/(`[^`]+`|\[[^\]\n]+\]\(https?:\/\/[^)\s]+\))/g).map((part) => {
    if (part.startsWith('`') && part.endsWith('`') && part.length > 1) return `<code>${escapeHTML(part.slice(1, -1))}</code>`;
    const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/);
    if (link) return `<a href="${escapeHTML(link[2])}" target="_blank" rel="noopener noreferrer">${escapeHTML(link[1])}</a>`;
    return citedText(part);
  }).join('');
}
// 小型安全 Markdown：先转义，再支持标题、列表、表格、引用块和代码块。
function markdown(text) {
  const lines = String(text).split('\n'); const html = [];
  for (let i = 0; i < lines.length;) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    if (/^#{1,6}\s/.test(line)) { html.push(`<h3>${inline(line.replace(/^#{1,6}\s+/, ''))}</h3>`); i++; continue; }
    if (line.startsWith('```')) {
      const code = []; i++;
      while (i < lines.length && !lines[i].startsWith('```')) code.push(lines[i++]);
      html.push(`<pre><code>${escapeHTML(code.join('\n'))}</code></pre>`); i++; continue;
    }
    if (i + 1 < lines.length && line.includes('|') && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1])) {
      const cells = (row) => row.trim().replace(/^\||\|$/g, '').split('|');
      const head = cells(line); i += 2; const rows = [];
      while (i < lines.length && lines[i].includes('|') && lines[i].trim()) rows.push(cells(lines[i++]));
      html.push(`<div class="table-wrap"><table><thead><tr>${head.map((c) => `<th>${inline(c)}</th>`).join('')}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
      continue;
    }
    const list = line.match(/^\s*(?:([-*])|(\d+)\.)\s+/);
    if (list) {
      const tag = list[2] ? 'ol' : 'ul'; const pattern = tag === 'ol' ? /^\s*\d+\.\s+/ : /^\s*[-*]\s+/; const items = [];
      while (i < lines.length && pattern.test(lines[i])) items.push(`<li>${inline(lines[i++].replace(pattern, ''))}</li>`);
      html.push(`<${tag}>${items.join('')}</${tag}>`); continue;
    }
    if (/^>\s?/.test(line)) { html.push(`<blockquote>${inline(line.replace(/^>\s?/, ''))}</blockquote>`); i++; continue; }
    const paragraph = [line]; i++;
    while (i < lines.length && lines[i].trim() && !/^(?:#{1,6}\s|[-*]\s|\d+\.\s|>|```)/.test(lines[i]) && !(i + 1 < lines.length && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1]))) paragraph.push(lines[i++]);
    html.push(`<p>${paragraph.map(inline).join('<br>')}</p>`);
  }
  return html.join('');
}

// ---------- 结果 ----------
function routeLabel(r) {
  if (r.status === 'failed') return r.mode === 'rag' ? 'RAG' : r.mode === 'agent' ? 'Agent' : 'Auto';
  if (r.mode === 'auto') return (r.route || '').includes('Agent') ? t('meta.autoAgent') : t('meta.autoDirect');
  return r.mode === 'agent' ? 'Agent' : 'RAG';
}
function renderResultMeta(r) {
  const api = r.api_summary || {}; const usage = api.reported_usage || {};
  const parts = [];
  if (r.origin === 'saved') parts.push(`<span class="replay">${escapeHTML(t('meta.replay'))}</span>`);
  parts.push(`<span class="route">${escapeHTML(routeLabel(r))}</span>`);
  if (r.network?.papers_read) parts.push(`<span>${escapeHTML(t('meta.web', { n: r.network.papers_read }))}</span>`);
  if (api.attempts != null) parts.push(`<span>${escapeHTML(api.failed_attempts ? t('meta.requestsFailed', { n: api.attempts, f: api.failed_attempts }) : t('meta.requests', { n: api.attempts }))}</span>`);
  if (usage.total_tokens) parts.push(`<span>${escapeHTML(t('meta.tokens', { n: number(usage.total_tokens) }))}</span>`);
  if (r.elapsed != null) parts.push(`<span>${escapeHTML(t('meta.seconds', { n: seconds(r.elapsed) }))}</span>`);
  $('resultMeta').innerHTML = parts.join('');
}
function bannerFor(r) {
  if (r.status === 'failed') return null;
  const key = r.answer_status === 'source_unavailable' ? 'banner.unavailable'
    : r.answer_status === 'insufficient_evidence' ? 'banner.insufficient'
    : r.answer_status === 'review_failed' ? 'banner.reviewFailed'
    : r.answer_status === 'citation_failed' ? 'banner.citationFailed'
    : r.status === 'degraded' ? 'banner.degraded' : null;
  return key ? t(key) : null;
}
function detailRow(label, value, raw) {
  return `<dt>${escapeHTML(label)}</dt><dd>${value}${raw ? `<span class="raw">${escapeHTML(raw)}</span>` : ''}</dd>`;
}
function renderDetails(r) {
  const api = r.api_summary || {}; const usage = api.reported_usage || {};
  const external = r.citations.filter((c) => c.origin === 'arxiv').length;
  const rows = [];
  const route = r.mode === 'auto' ? ((r.route || '').includes('Agent') ? t('route.escalated') : t('route.direct')) : t(`route.${r.mode === 'agent' ? 'agent' : 'rag'}`);
  rows.push(detailRow(t('details.route'), escapeHTML(route), r.route));
  if (r.stop_reason) {
    const human = STRINGS.zh[`stop.${r.stop_reason}`] ? t(`stop.${r.stop_reason}`) : '';
    rows.push(detailRow(t('details.stop'), escapeHTML(human), r.stop_reason));
  }
  rows.push(detailRow(t('details.answer'), escapeHTML(STRINGS.zh[`status.${r.answer_status}`] ? t(`status.${r.answer_status}`) : ''), r.answer_status));
  rows.push(detailRow(t('details.passages'), escapeHTML(t('details.passagesValue', { n: r.citations.length, m: state.index.cited.length }) + (external ? t('details.external', { k: external }) : ''))));
  if (r.local_coverage) rows.push(detailRow(t('details.coverage'), escapeHTML(t('details.coverageValue', { a: r.local_coverage.supported, b: r.local_coverage.total }))));
  if (r.actions?.length) {
    const items = r.actions.map((a) => {
      const label = STRINGS.zh[`tool.${a.tool}`] ? t(`tool.${a.tool}`) : a.tool;
      const status = STRINGS.zh[`tool.${a.status}`] ? t(`tool.${a.status}`) : a.status;
      return `<li class="${a.status === 'failed' ? 'failed' : ''}">${escapeHTML(label + colon() + status)}</li>`;
    });
    rows.push(detailRow(t('details.actions'), `<ul>${items.join('')}</ul>`));
  }
  const net = r.network || {};
  const web = net.status === 'not_requested' ? t('details.webOff')
    : net.http_tool_calls ? t('details.webValue', { n: net.http_tool_calls, k: net.papers_read || 0 })
    : (STRINGS.zh[`web.${net.status}`] ? t(`web.${net.status}`) : '');
  rows.push(detailRow(t('details.web'), escapeHTML(web), net.status !== 'not_requested' ? net.status : ''));
  if (api.attempts != null) rows.push(detailRow(t('details.requests'), escapeHTML(t('details.requestsValue', { n: api.attempts, f: api.failed_attempts || 0, r: api.automatic_retries || 0 }))));
  if (usage.total_tokens) rows.push(detailRow(t('details.tokens'), escapeHTML(t('details.tokensValue', { i: number(usage.prompt_tokens), o: number(usage.completion_tokens) }))));
  const sameLibrary = state.meta && r.kb_version === state.meta.kb_version;
  rows.push(detailRow(t('details.library'), sameLibrary ? escapeHTML(t('details.libraryValue', { n: state.meta.papers.length, c: number(state.meta.chunks) })) : '', r.kb_version));
  if (r.date) rows.push(detailRow(t('details.date'), escapeHTML(r.date)));
  $('runList').innerHTML = rows.join('');
}
function cleanPassage(c) {
  let text = String(c.text || '');
  const prefix = `Title: ${c.title || ''}`;
  if (c.title && text.startsWith(prefix)) text = text.slice(prefix.length).trimStart();
  // PDF 换行留下的 "knowl- edge"：只去掉空格，保留连字符，不猜测单词。
  text = text.replace(/([a-z])- ([a-z])/g, '$1-$2');
  // 段落从句子中间开始时（首字母小写），加省略号提示前文被截断。
  return /^[a-z]/.test(text) ? '…' + text : text;
}
function renderSources() {
  const r = state.result; if (!r) return;
  const { cited, display } = state.index;
  const external = r.citations.filter((c) => c.origin === 'arxiv' && cited.includes(c.number)).length;
  $('sourcesCount').textContent = cited.length ? (external ? t('sources.citedWeb', { m: cited.length, k: external }) : t('sources.cited', { m: cited.length })) : '';
  const list = r.citations.filter((c) => state.showUncited || cited.includes(c.number)).sort((a, b) => display.get(a.number) - display.get(b.number));
  $('sources').innerHTML = list.length ? list.map((c) => {
    const open = state.sel === c.number;
    const page = c.page == null ? t('sources.noPage') : t('sources.page', { p: c.page });
    const arxiv = c.origin === 'arxiv';
    const sub = [];
    if (c.section && c.section !== 'None') sub.push(`<span>${escapeHTML(c.section)}</span>`);
    if (arxiv) sub.push(`<span class="ext-tag">arXiv ${escapeHTML(String(c.source || '').replace(/\.pdf$/i, ''))}</span>`);
    if (c.url) sub.push(`<a href="${escapeHTML(c.url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(t('sources.openPdf'))}</a>`);
    return `<div class="source${open ? ' open' : ''}${cited.includes(c.number) ? '' : ' uncited'}" id="src-${c.number}">
      <button type="button" class="source-head" data-src="${c.number}" aria-expanded="${open}" aria-controls="passage-${c.number}">
        <span class="cite">${display.get(c.number)}</span>
        <span class="source-title" title="${escapeHTML(c.title || c.source)}">${escapeHTML(c.title || c.source)}</span>
        <span class="source-page">${escapeHTML(page)}</span>
      </button>
      ${sub.length ? `<div class="source-sub">${sub.join('')}</div>` : ''}
      <p class="passage" id="passage-${c.number}">${escapeHTML(cleanPassage(c))}</p>
    </div>`;
  }).join('') : `<p class="sources-empty">${escapeHTML(t('sources.none'))}</p>`;
  const uncited = r.citations.length - cited.length;
  $('moreSources').hidden = uncited <= 0;
  $('moreSources').textContent = state.showUncited ? t('sources.less') : t('sources.more', { n: uncited });
}
function select(n, scroll = true) {
  state.sel = state.sel === n ? null : n;
  if (state.sel != null && !state.index.cited.includes(state.sel)) state.showUncited = true;
  document.querySelectorAll('#answer .cite').forEach((el) => el.classList.toggle('on', Number(el.dataset.n) === state.sel));
  document.querySelectorAll('#answer .claim').forEach((el) => el.classList.toggle('lit', state.sel != null && el.dataset.cites.split(' ').map(Number).includes(state.sel)));
  renderSources();
  const card = state.sel != null && $('src-' + state.sel);
  if (card && scroll) {
    const panel = $('sourcesPanel');
    if (getComputedStyle(panel).position === 'sticky') {
      const head = panel.querySelector('.sources-head').offsetHeight;
      panel.scrollTo({ top: panel.scrollTop + card.getBoundingClientRect().top - panel.getBoundingClientRect().top - head - 8, behavior: 'smooth' });
    } else card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}
function renderResult(r, fresh = true) {
  state.result = r; state.lost = false;
  if (fresh) { state.sel = null; state.showUncited = false; state.editing = false; placeComposer(); }
  state.index = citationIndex(r);
  reading(true); showView('ask');
  $('sourcesPanel').hidden = false;
  $('resultQuestion').textContent = r.query;
  $('runningView').hidden = true;
  renderResultMeta(r);
  if (r.status === 'failed') {
    $('answerView').hidden = true; $('statusBanner').hidden = true;
    showProblem(t('failed.title'), r.answer, t('failed.hint'), true);
    renderSources();
    return;
  }
  $('problemView').hidden = true; $('answerView').hidden = false;
  const banner = bannerFor(r);
  $('statusBanner').hidden = !banner; $('statusBanner').textContent = banner || '';
  $('answer').innerHTML = markdown(r.answer);
  $('disclaimer').textContent = r.answer_status === 'review_passed' ? t('disclaimer.reviewed') : r.answer_status === 'not_reviewed' ? t('disclaimer.checked') : t('disclaimer.other');
  renderDetails(r);
  renderSources();
  if (state.sel != null) { const keep = state.sel; state.sel = null; select(keep, false); }
}
function showProblem(title, body, hint, failed) {
  $('answerView').hidden = true; $('runningView').hidden = true; $('problemView').hidden = false;
  $('problemTitle').textContent = title;
  $('problemBody').textContent = body || '';
  $('problemHint').textContent = hint || '';
  $('problemService').textContent = failed && state.config?.base_url ? t('failed.service', { url: state.config.base_url }) : '';
  const actions = [];
  if (failed) actions.push(`<button type="button" class="btn btn-primary" data-action="settings">${escapeHTML(t('failed.settings'))}</button>`);
  actions.push(`<button type="button" class="btn${failed ? '' : ' btn-primary'}" data-action="retry">${escapeHTML(t('failed.retry'))}</button>`);
  if (!failed) actions.push(`<button type="button" class="btn" data-action="new">${escapeHTML(t('result.new'))}</button>`);
  $('problemActions').innerHTML = actions.join('');
}
function showLost() {
  state.lost = true; state.result = null; reading(true);
  const saved = recall();
  $('resultQuestion').textContent = saved.query || $('question').value || '';
  $('resultMeta').innerHTML = ''; $('statusBanner').hidden = true;
  showProblem(t('lost.title'), t('lost.body'), '', false);
  $('sourcesPanel').hidden = true;
}
$('problemActions').addEventListener('click', (event) => {
  const action = event.target.closest('[data-action]')?.dataset.action;
  if (action === 'settings') openSettings();
  if (action === 'retry') {
    const query = state.result?.query || $('resultQuestion').textContent;
    state.editing = true; $('question').value = query; placeComposer(); $('question').focus();
  }
  if (action === 'new') home();
});
$('answer').addEventListener('click', (event) => {
  const cite = event.target.closest('.cite'); if (cite) select(Number(cite.dataset.n));
});
$('sources').addEventListener('click', (event) => {
  const head = event.target.closest('[data-src]'); if (head) select(Number(head.dataset.src), false);
});
$('moreSources').addEventListener('click', () => { state.showUncited = !state.showUncited; renderSources(); });
$('copyButton').addEventListener('click', async () => {
  const r = state.result; if (!r) return;
  const lines = r.citations.filter((c) => state.index.cited.includes(c.number))
    .map((c) => `[${c.number}] ${c.title || c.source}, ${c.page == null ? '—' : t('answer.page', { p: c.page })}`);
  try { await navigator.clipboard.writeText(`${r.answer}\n\n${t('answer.copySources')}\n${lines.join('\n')}`); toast(t('answer.copied')); }
  catch { toast(t('answer.copyFailed')); }
});

// ---------- 已保存的回答 ----------
async function loadExample(id) {
  if (state.busy || state.loading) return;
  const request = ++state.exampleRequest; state.loading = true; syncControls();
  try {
    const result = await api('/api/examples/' + encodeURIComponent(id));
    if (request !== state.exampleRequest) return;
    notice('');
    $('question').value = result.query; renderResult(result); remember({ example: id });
    window.scrollTo({ top: 0 });
  } catch (error) { if (error.offline) offline(); else notice(error.message); }
  finally { if (request === state.exampleRequest) { state.loading = false; syncControls(); } }
}
$('examples').addEventListener('click', (event) => {
  const ex = event.target.closest('[data-example]'); if (ex) loadExample(ex.dataset.example);
});

// ---------- 论文库 ----------
function renderLibrary() {
  const meta = state.meta; if (!meta) return;
  $('libraryLede').textContent = t('library.lede', { n: meta.papers.length, c: number(meta.chunks) });
  const filter = $('librarySearch').value.trim().toLowerCase();
  const papers = meta.papers.filter((p) => `${p.title} ${p.source}`.toLowerCase().includes(filter));
  $('libraryRows').innerHTML = papers.length ? papers.map((p) => `<li><strong>${escapeHTML(p.title || p.source)}</strong><span>${escapeHTML(t('library.passages', { n: p.chunks }) + sep() + p.source)}</span></li>`).join('')
    : `<li class="muted">${escapeHTML(t('library.empty'))}</li>`;
  const files = $('paperFiles').files;
  $('fileSummary').textContent = files.length ? t('library.files', { n: files.length }) : t('library.noFiles');
}
$('librarySearch').addEventListener('input', renderLibrary);
$('paperFiles').addEventListener('change', renderLibrary);
$('homeAddPapers').addEventListener('click', () => { showView('library'); $('paperFiles').focus(); });
document.querySelectorAll('[data-view]').forEach((el) => el.addEventListener('click', () => {
  if (el.dataset.view === 'ask' && state.view === 'ask' && !state.busy) home(); else showView(el.dataset.view);
}));
function importStatus(text, error = false) {
  $('importStatus').textContent = text; $('importStatus').classList.toggle('error', error);
}
let importTimer;
async function watchImport(id) {
  clearTimeout(importTimer);
  try {
    const job = await api('/api/imports/' + id);
    const skipped = job.skipped?.length ? ' ' + t('library.skipped', { list: job.skipped.join('、') }) : '';
    importStatus((job.stage || '') + (job.error ? '：' + job.error : '') + skipped, job.status === 'failed');
    if (job.status === 'running') { $('uploadButton').disabled = true; importTimer = setTimeout(() => watchImport(id), 1500); return; }
    $('uploadButton').disabled = false;
    try { localStorage.removeItem('paperlens.import'); } catch {}
    if (job.status === 'completed') { await loadMeta(); toast(t('library.done')); }
  } catch (error) {
    $('uploadButton').disabled = false;
    if (error.status === 404) { try { localStorage.removeItem('paperlens.import'); } catch {} return; }
    importStatus(error.message, true);
  }
}
$('uploadForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const files = Array.from($('paperFiles').files);
  if (!files.length || files.length > 5 || files.reduce((s, f) => s + f.size, 0) > 20 * 1024 * 1024) { importStatus(t('library.badFiles'), true); return; }
  $('uploadButton').disabled = true; importStatus(t('library.uploading'));
  try {
    const encoded = await Promise.all(files.map((file) => new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve({ name: file.name, data: String(reader.result).split(',')[1] });
      reader.onerror = () => reject(new Error(file.name));
      reader.readAsDataURL(file);
    })));
    const job = await postJSON('/api/imports', { files: encoded, two_columns: $('twoColumns').checked });
    try { localStorage.setItem('paperlens.import', job.id); } catch {}
    $('paperFiles').value = ''; renderLibrary();
    watchImport(job.id);
  } catch (error) { $('uploadButton').disabled = false; importStatus(error.message, true); }
});

// ---------- 模型设置 ----------
const cfg = { models: [], request: 0 };
function refreshSettingsText() {
  const c = state.config || {};
  const env = c.key_source === 'environment';
  const state_ = env ? t('settings.keyEnv') : c.has_key ? t('settings.keySaved') : t('settings.keyMissing');
  $('keyState').textContent = state_;
  $('keyState').classList.toggle('missing', !c.has_key);
  $('cfgKey').placeholder = env ? t('settings.keyEnvPh') : c.has_key ? t('settings.keyKeep') : t('settings.keyNew');
  $('modelHelp').textContent = c.model ? t('settings.modelHelp', { m: c.model }) : t('settings.modelHelpNone');
  $('optionsNote').textContent = t('settings.options');
  checkSettings();
}
function checkSettings() {
  const c = state.config || {};
  const base = $('cfgBase').value.trim().replace(/\/+$/, '');
  const saved = (c.base_url || '').replace(/\/+$/, '');
  const changed = base !== saved;
  $('keyWarn').hidden = !(changed && saved && !$('cfgKey').value.trim() && c.key_source !== 'environment');
  $('optionsNote').hidden = !(c.has_options && (changed || $('cfgModel').value.trim() !== (c.model || '')));
}
// 打开列表时显示全部模型；只有用户正在输入时才按输入过滤。
function renderModelList(open, filter = false) {
  const list = $('modelList');
  if (!cfg.models.length || !open) { list.hidden = true; $('cfgModel').setAttribute('aria-expanded', 'false'); return; }
  const q = filter ? $('cfgModel').value.trim().toLowerCase() : '';
  const current = state.config?.model;
  const shown = cfg.models.filter((m) => !q || m.toLowerCase().includes(q));
  list.innerHTML = shown.length ? shown.map((m) => `<li><button type="button" data-model="${escapeHTML(m)}"${m === current ? ' aria-current="true"' : ''}>${escapeHTML(m)}</button></li>`).join('')
    : `<li class="empty">${escapeHTML(t('settings.noMatch'))}</li>`;
  list.hidden = false; $('cfgModel').setAttribute('aria-expanded', 'true');
}
async function openSettings() {
  try { state.config = await api('/api/config'); }
  catch (error) { if (error.offline) offline(); else notice(error.message); return; }
  const c = state.config;
  cfg.models = []; cfg.request++;
  $('cfgBase').value = c.base_url || '';
  $('cfgModel').value = c.model || '';
  $('cfgKey').value = '';
  $('cfgKey').disabled = c.key_source === 'environment';
  $('fetchStatus').textContent = ''; $('fetchStatus').classList.remove('error');
  $('saveError').hidden = true;
  $('modelToggle').hidden = true; $('modelList').hidden = true;
  $('settingsSave').disabled = false; $('settingsSave').textContent = t('settings.save');
  refreshSettingsText();
  $('settingsDialog').showModal();
}
$('modelButton').addEventListener('click', openSettings);
$('cfgBase').addEventListener('input', () => { cfg.models = []; cfg.request++; $('modelToggle').hidden = true; renderModelList(false); checkSettings(); });
$('cfgKey').addEventListener('input', checkSettings);
$('cfgModel').addEventListener('input', () => { renderModelList(true, true); checkSettings(); });
$('cfgModel').addEventListener('focus', () => renderModelList(true));
$('cfgModel').addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !$('modelList').hidden) { event.preventDefault(); renderModelList(false); }
  if (event.key === 'ArrowDown' && !$('modelList').hidden) { event.preventDefault(); $('modelList').querySelector('button')?.focus(); }
});
$('modelToggle').addEventListener('click', () => renderModelList($('modelList').hidden));
$('modelList').addEventListener('click', (event) => {
  const b = event.target.closest('[data-model]'); if (!b) return;
  $('cfgModel').value = b.dataset.model; renderModelList(false); checkSettings(); $('cfgModel').focus();
});
$('modelList').addEventListener('keydown', (event) => {
  const items = [...$('modelList').querySelectorAll('button')]; const i = items.indexOf(document.activeElement);
  if (event.key === 'ArrowDown') { event.preventDefault(); items[Math.min(i + 1, items.length - 1)]?.focus(); }
  if (event.key === 'ArrowUp') { event.preventDefault(); if (i <= 0) $('cfgModel').focus(); else items[i - 1].focus(); }
  if (event.key === 'Escape') { event.preventDefault(); renderModelList(false); $('cfgModel').focus(); }
});
document.addEventListener('click', (event) => {
  if (!$('modelList').hidden && !event.target.closest('.model-box')) renderModelList(false);
});
$('fetchModels').addEventListener('click', async () => {
  const request = ++cfg.request;
  $('fetchModels').disabled = true; $('fetchModels').textContent = t('settings.fetching');
  $('fetchStatus').textContent = ''; $('fetchStatus').classList.remove('error');
  try {
    const result = await postJSON('/api/models', { base_url: $('cfgBase').value, api_key: $('cfgKey').value });
    if (request !== cfg.request || !$('settingsDialog').open) return;
    cfg.models = result.models || [];
    $('fetchStatus').textContent = cfg.models.length ? t('settings.fetched', { n: cfg.models.length }) : t('settings.fetchedEmpty');
    $('modelToggle').hidden = !cfg.models.length;
    if (cfg.models.length) { $('cfgModel').focus(); renderModelList(true); }
  } catch (error) {
    if (request !== cfg.request) return;
    $('fetchStatus').textContent = error.message; $('fetchStatus').classList.add('error');
  } finally {
    $('fetchModels').disabled = false; $('fetchModels').textContent = t('settings.fetch');
  }
});
$('settingsForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const model = $('cfgModel').value.trim();
  if (!model) { $('saveError').textContent = t('settings.needModel'); $('saveError').hidden = false; $('cfgModel').focus(); return; }
  $('saveError').hidden = true;
  $('settingsSave').disabled = true; $('settingsSave').textContent = t('settings.saving');
  const payload = { base_url: $('cfgBase').value, model, api_key: $('cfgKey').value };
  try {
    state.config = await postJSON('/api/config', payload);
    $('cfgKey').value = '';
    $('settingsDialog').close();
    await loadMeta();
    toast(t('settings.saved'));
  } catch (error) {
    $('saveError').textContent = error.message; $('saveError').hidden = false;
  } finally {
    payload.api_key = '';
    $('settingsSave').disabled = false; $('settingsSave').textContent = t('settings.save');
  }
});
$('settingsCancel').addEventListener('click', () => $('settingsDialog').close());
$('settingsDialog').addEventListener('close', () => { $('cfgKey').value = ''; renderModelList(false); });

// ---------- 帮助、语言 ----------
$('helpButton').addEventListener('click', () => $('helpDialog').showModal());
document.querySelectorAll('.dialog').forEach((dialog) => dialog.addEventListener('click', (event) => {
  if (event.target !== dialog) return;
  const r = dialog.getBoundingClientRect();
  if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();
}));
document.querySelectorAll('[data-lang]').forEach((el) => el.addEventListener('click', () => {
  lang = el.dataset.lang;
  try { localStorage.setItem('paperlens.lang', lang); } catch {}
  applyLanguage();
}));

// ---------- 启动 ----------
async function loadMeta() {
  state.meta = await api('/api/meta');
  try { state.config = await api('/api/config'); } catch {}
  renderMeta(); renderHome(); renderLibrary();
}
async function reconnect() {
  try {
    await loadMeta();
    if (state.job) poll(state.job);
  } catch (error) { if (error.offline) offline(); else notice(error.message); }
}
async function init() {
  applyLanguage();
  const saved = recall();
  $('question').value = saved.query || '';
  if (['auto', 'rag', 'agent'].includes(saved.mode)) state.mode = saved.mode;
  state.net = state.mode !== 'rag' && saved.net === true;
  syncControls();
  try { await loadMeta(); }
  catch (error) { if (error.offline) offline(); else notice(error.message); return; }
  if (saved.job) { state.busy = true; state.job = saved.job; syncControls(); reading(true); renderRunning(0, saved.query); poll(saved.job); }
  else if (saved.example) loadExample(saved.example);
  let pending = null; try { pending = localStorage.getItem('paperlens.import'); } catch {}
  if (pending) watchImport(pending);
}
init();
