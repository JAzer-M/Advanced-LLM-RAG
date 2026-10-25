# Advanced-LLM-RAG 当前进度与交接

更新：2026-10-25（Asia/Shanghai）。工作区 `/Users/j/Desktop/Advanced-LLM-RAG`，分支 `main`。

**10月25日本轮已完成：** 按用户批准方案实现来源范围/检索正文分离、有限断行引文兼容、题头需求绑定、语言/首段提示、原11次预算内的Agent降级回退与新评分适配。新16篇52题、1459段独立库，312生成/312判分均完成；26题GLM 5.3 Flash、26题GLM 5.3，逐题六路同模型。完整答案F1：RAG19.67→20.00、Agent16.28→20.60、Auto19.62→19.49；模型correct为32→35、26→36、34→34。Agent无交付失败12→0但10条降级，7条原completed转degraded；Auto生成token少35.4%，不能把首段F1上升或状态完成当成完整事实正确。后端378、网页43、并行监督2项通过；本轮1495请求/2,990,205已报告token，3条错误缺usage。旧实验、旧文件字节与两库指针保留。[完整报告](evaluation/results/qasper_improvement_20261025/report.md) · [源码/资产/官方复算核验](evaluation/results/qasper_improvement_20261025/verification.json) · [原文抽查与退步](evaluation/results/qasper_improvement_20261025/manual_review.md)。以下10月24日分数是历史记录，不归给修正版。

**本机PaperLens可用RAG、Agent、Auto、引用原文、模型设置和PDF入库。** 中文比较绑定与JSON代码块已有修复；新题仍发现全缺失/修订路径的语言遗漏、同篇方法串用和错误拒答，未声称全部质量问题已解决。最新离线回归为后端378、网页43项，新增评测监督检查另有2项。Mac预览包、Windows源码/安装包验收是10月24日历史交付；本轮仅修改源码与评测，没有重建安装包或发布。签名公证、另一台Mac及v0.2.0 Release仍按原交付计划处理。[实验总览](docs/PROJECT_METRICS.md) · [安装验收](docs/maintenance/installation_ui_acceptance_20261024/report.md) · [下载包验收](docs/maintenance/macos_package_20261024/report.md)

本页记录当前状态与剩余工作；日期报告记录当时状态。整理前完整进度已逐字节保存到[2026-10-24历史快照](docs/history/PROGRESS_BEFORE_P4_CLOSEOUT_2026-10-24.md)，此前多轮记录见[截至10月22日的完整历史](docs/history/PROGRESS_THROUGH_2026-10-22.md)。桌面总览与[PROJECT_WORKFLOW](docs/PROJECT_WORKFLOW.md)只表示预期路线。

## 1. 阶段状态

| 阶段 | 已完成 | 边界与后续 |
| --- | --- | --- |
| 基础 RAG 与检索改进 | PDF解析、分块、混合检索、RRF、重排、分解、原文保留、规则补查及引用检查 | 分块不保证无损，引用结构通过不等于事实正确 |
| P0 论文与知识库 | 3/5/8篇版本与校验、切换、回退；网页PDF批量入库、内容去重、独立版本发布 | 网页当前9篇；Windows导入锁已适配；OCR、删除、网页回退、arXiv链接导入未完成 |
| P1 评测基线 | 检索量化与12题固定RAG基线，逐题Gold、人工审阅及实际成本 | 同助手出题/审阅、小样本；不是第三方盲评 |
| P2 Agent / Auto | main三模式、需求绑定、证据判断、本地工具、预算循环、回答复核；中文比较句修复 | 已有QASPER52题模型轮换实测；单模型泛化收益未证明，隐性漏答可能不触发Auto升级 |
| P3 联网证据 | 显式arXiv搜索、固定版本PDF、独立来源与引用、失败诊断和有限交付 | 默认关闭；不是通用网页搜索，不自动入库；外部可用性不保证 |
| P4 界面与交付 | 暖白/朱橙前端、引用联动、中英文、Enter发送；文档/分版本实验整理；Mac独立环境安装及操作验收；Mac预览下载包（含权重冷下载、续传、三模式问答与重启验收） | Windows已据用户记录完成人工验收；签名公证、另一台Mac、v0.2.0 Release和求职材料另做 |

## 2. 当前三条执行路径

| 路径 | 实际行为 | 默认版本与预算 |
| --- | --- | --- |
| 固定 RAG | 分解→Dense/BM25→RRF→BGE与局部证据→规则补查→生成与引用检查 | 未传版本读全局激活库；常规完整题通常2请求 |
| 固定 Agent | 共用初检→规划需求→逐项检查→搜索/读邻段/停止→回答与有限复核；本地失败且有预算时RAG后备降级交付 | 未传版本用八篇实验基线；含分解及回退最多11请求 |
| Auto | 先生成RAG草稿；明确缺口、无法回答/比较或引用失败时升级Agent | 未传版本用八篇实验基线；直答通常2请求，最坏13请求 |

Python函数默认 `mode='rag'`；CLI默认 `--mode auto`。三模式都能显式选择合法配对版本；同库比较必须显式选同一版本。网页从自己的指针取得版本，在提交时固定，三模式共用同一网页库，不改变全局激活指针。

Agent工具最多3行动；规划/状态修正或重复行动改选共用一次修正额度。回答最多初稿、复核、修订、再复核4次；全部missing直接列缺口，不新增回答调用。原文最多32段/24000字符。

`--allow-network`仅对Agent/Auto开放arXiv，另加最多3次模型决策；总模型上限分别14/16，公网工具最多1次搜索和1次固定版本PDF读取。库中明确已有主论文时不走外部补证据，开关开启不表示每题都会联网。外部材料用于当前任务，不自动进入永久库。

失败不自动重试；`finish_reason='length'`算未完成。三模式保留状态、非空答案/说明、原文、行动、停止原因与实际成本。Auto升级失败时仅引用结构合格的草稿允许有限降级交付；Agent本地失败的新增RAG回退共享原预算、保留原错误且不称复核通过。429/超时只能说明暂时无法获取原文，不能断言论文未报告。`completed`与`review_passed`均不是独立准确率标签。[返回约定](docs/BACKEND_RESULT.md)

## 3. 已有质量与成本证据

[PROJECT_METRICS](docs/PROJECT_METRICS.md)是分版本数字总入口，覆盖P1基线、P2.5十二题、第一版Auto八题、P3六题及两题Auto、检索Top-10/20和后续开发回归。旧失败计入计划分母，修复后单题结果不回填旧分数。

| 最新已验证事项 | 结果与证据 |
| --- | --- |
| 中文比较需求绑定 | “VGG和RAG的区别是什么？”保留跨方法比较；仅两处规则变化，新增3项测试。[修复报告](evaluation/results/chinese_comparison_20261024/report.md) |
| 全套行为回归 | 后端345项、网页27项通过；网页首次2项临时端口权限错误保留，允许本机端口后通过。[最终汇总](evaluation/results/chinese_comparison_20261024/final_offline_test_summary.json) |
| 原中文问题真实Agent | `cn:glm-5.3`，completed/review_passed；102.13秒、9请求、34320 token，1次读邻段，arXiv/自动重试0。核心任务/机制及引用人工核对通过。[结果](evaluation/results/chinese_comparison_20261024/live_summary.json) · [人工核对](evaluation/results/chinese_comparison_20261024/manual_review.json) |
| 回答语言与JSON兼容 | 跟随提问语言，明确指定时优先；整段JSON代码块可解析，字段校验保持。10月24日已有中/英文Auto及中文Agent真实记录，见实验总览 |
| PDF入库 | 本地Mamba新增370段，网页达到9篇1767段；真实本地RAG为13.62秒、2请求、2965 token，第1页引用核对通过。[入库日志](docs/WEBUI_PDF_IMPORT_2026-10-24.md) |

上述中文Agent及345/27测试属于前一轮记录；其后的文档整理没有新增模型调用。本轮安装与前端验收另外新增一次VGG固定RAG：新建1篇/160段库，20.32秒、2请求、3098 token，答案和第2页引用核对通过。获取模型列表另有1次网关`/models`请求；PDF入库与案例回放不新增生成调用。CLI帮助文字的旧八篇限制已与实际默认/显式版本行为统一。

**QASPER外部题集评测（10月24日，本次新增）：** 已有15篇52题、独立库1612段；原交接中“未抽样/未建库”已过时。原GLM运行遇429；未绑定目标论文的DeepSeek轮保存18条后因输入缺陷中断。新轮只补题名/arXiv编号，题号、Gold、库、生产逻辑和评分不变，保留旧轮及成本。完成156条生成（134 completed、5 degraded、17 failed）和156条匹配作答模型的判分。Answer F1为RAG14.83、Agent14.81、Auto21.39；近似Evidence F1为28.24/41.22/33.00，官方脚本复算一致。每题三模式同模型，但全体39/10/3题分属三种模型；判分correct为25/25/28，不称人工准确率。全部已留档885次模型请求、1,859,159 token，另有未落盘分解用量；正式轮含判分为819请求、1,740,096 token。完整模型切换、失败、抽查、成本与边界见[报告](evaluation/results/qasper_20261024/report.md)、[汇总](evaluation/results/qasper_20261024/summary.json)。

**10月24日发现的边界：** 拒答启发式至少有一处明确误标和一处漏标；部分英文问题得到中文输出。原GLM已通过的语言回归保留，但不再将其外推到所有模型。Agent仍有需求引文、一次修正额度及最终复核失败。本轮未据结果改分或调生产代码，也没有重跑旧345/42项测试；执行层3项离线检查通过。

**10月25日新论文配对（本轮）：** 原版`54fa038`与修正版同题同库对照已完成，见顶部与[报告](evaluation/results/qasper_improvement_20261025/report.md)。完整F1差值的论文簇区间均含0；模型判分仅Agent的correct增益区间为正。修正版Agent36/52模型correct只比同版RAG35/52多1条，却消耗约4.93倍生成token；不能宣称Agent/Auto普遍优于RAG。固定24份来源核对保留了分类器事实补全、相关工作串用、CCPC段落排68导致错误拒答及Gold二元标注分歧。旧/新各52题不混成一个泛化分数；当前新题已被观察，后续作开发诊断而非再次冒充独立验收。

## 4. 优先级与下一步

完整性仍按用户已确认的顺序：必须回答明确需求及影响结论的条件，避免编造和错引；按任务补充复现步骤；不为无关背景满分反复调试。

**已关闭的待办：** 中文“区别是什么”需求绑定、已知题语言回归（新题仍有遗漏）、JSON代码块兼容、旧8848页面退役、网页PDF入库及此前全套测试核对。此前文档与实验整理已保留本地提交`2dbe1dd`。本轮完成Mac独立虚拟环境安装、启动、空库首篇建库及前端操作；修复缺少历史库时首页500、首次导入失败、VGG标题截成首字母和过期输入提示残留。用户确认真实中文输入法选词Enter不误发送。[安装说明](docs/INSTALL_AND_START.md)

**Mac 预览下载包（10月24日）：** 用户数据迁至`~/Library/Application Support/PaperLens/`，冻结程序自启后台进程，首次启动下载固定版本MiniLM/BGE（1.61 GB，可中断续传，完成前禁止上传），网页增加退出按钮。PyInstaller三次构建（缓存权限失败、torchvision本地库缺失、成功），生成`releases/PaperLens-0.1.0-macos-arm64-preview.zip`（276 MB，ad-hoc签名）。解压版从空数据目录和空模型缓存完成入库及RAG/Agent/Auto问答：9请求、17168 token、0失败；重复上传、无正文PDF、退出与重启通过；包内无密钥、论文或权重。验收由Codex完成，报告由Claude据原始记录补写。[报告](docs/maintenance/macos_package_20261024/report.md) · [构建说明](packaging/macos/README.md)

**发布准备（10月24日）：** README改为展示页（截图、架构图、检索消融与回答对照、局限），旧版全文存于[历史目录](docs/history/README_BEFORE_SHOWCASE_2026-10-24.md)；新增MIT许可与GitHub Actions离线测试（CPU版torch，干净克隆中跳过1项依赖本机八篇库的测试）；`docs/chat_history/`改为仅本机保存，并已从未推送的历史中移除；同时把未推送提交的作者统一为JAzer-M，提交号因此变化，对照见[历史改写记录](docs/maintenance/history_rewrite_20261024.md)。干净克隆中后端345项（跳过1）、网页42项通过；CI已在GitHub上通过（ubuntu）。

**Windows 适配（10月24日，用户人工验收已记录）：** 入库/模型准备的`fcntl`锁改为跨平台`try_lock`（Windows用msvcrt）；进程存活检查改为`pid_alive`，避免Windows上`os.kill(pid,0)`实际发送Ctrl+C；冻结版Windows数据目录为`%LOCALAPPDATA%\PaperLens`；新增`webui/start.bat`（UTF-8模式、网页内下载模型）及安装说明第7节；CI的windows-latest已通过（后端与网页测试），现为正式检查。用户已在真实Windows电脑上按源码方式人工验收：模型下载、配置、入库、问答与引用、输入法回车、重复上传、刷新接续和重启均正常；期间一次中文提问未得到答案，重试后正常，原因未定位。

**Windows 安装包（10月24日）：** 版本号改为0.2.0；新增`packaging/windows/`（PyInstaller无控制台构建，启用UTF-8模式，构建时在源码目录外自检并核对`utf8_mode=1`）和`build-windows`工作流（手动或推送`v*`标签触发，产物为Actions Artifact）。冻结入口在无标准流时改写到空设备，自检结果同时写入数据目录。GitHub Actions首次构建即成功（自检通过、UTF-8模式生效）；用户在真实Windows电脑上用安装包人工验收通过。待发布为`v0.2.0`。

**接下来交付工作：**

1. 发布Windows `v0.2.0` Release（用户验收已记录）；可选重建Mac 0.2.0包并带上断线提示更新。Mac预览Release已发布的依据来自Claude会话，本轮未复核线上状态。签名公证、另一台Mac验收仍可后续处理。[下载包验收](docs/maintenance/macos_package_20261024/report.md)
2. 准备架构图、代表性案例、项目讲解和求职材料，效果描述引用实验总览及原始记录。
3. QASPER新题配对已完成。后续优先拆分来源范围与题名/正文的检索重排影响、核对同篇方法归属、调查7条completed→degraded、覆盖全缺失/修订语言分支，并修复空正文异常未保留usage。若再做质量验收，另取排除两轮已用论文的新题，不重跑回填本轮分数；更大单模型结论仍未建立。

本轮安装从`2dbe1dd`导出源码，叠加本轮必要修复后在独立`.venv`在线安装依赖；没有复用原虚拟环境或复制八/九篇版本。检索模型复用本机缓存，问答服务复用现有网关配置；权重全新下载、另一台机器及所有输入法均不在本轮结论内。

**历史缺陷与结论继续保留：** 10月23日英语VGG/RAG答案有附带联合微调句的引用覆盖缺口；该旧答案未改写，不能称全文引用通过。旧h10降级、P2.5规划失败、P3题名误拒绝和429/超时均保留在原报告。没有因本次中文修复就宣布这些历史实验全部通过，也未重新付费调试旧题。

**可延期：** 常驻模型提速、并发/多用户、持久问答会话、通用网页搜索、公网部署、arXiv链接入库、完整增量导入生命周期。当前仍有初始化与Agent额外请求成本；本轮不作速度收益结论。

## 5. 配置、知识库与关键约束

以下为2026-10-25本机核对值；模型设置可被用户改变，[本轮校验](evaluation/results/qasper_20261024/verification.json)保存当前公开选项与资产哈希检查，不含密钥；早期P4快照仍保留在历史验收目录。

| 项目 | 当前值 |
| --- | --- |
| Python / 本地模型 | `.venv` / 3.11.9；MiniLM `paraphrase-multilingual-MiniLM-L12-v2`，384维；`BAAI/bge-reranker-base`，CPU |
| 生成/分解模型 | 本机保存`cn:deepseek-v4.1-flash`；10月25日评测进程固定GLM 5.3 Flash/GLM 5.3，未改写保存设置；不混称单模型实验 |
| 生成选项 | thinking disabled、temperature 0、max_tokens 4096；私有配置留本机 |
| 候选与最终证据 | 每路及RRF候选120，RRF常数60；最终Top-10、子题局部Top-3 |
| 规则补查 | 按来源信号最多2轮；rewrite/HyDE关闭。检索评估须显式启用两轮，每个K独立选证据 |
| 资源与日志 | 受控CPU线程，离线加载已缓存Embedding/BGE；真实生成仍调用API。新运行使用新空目录，不改旧协议哈希续写 |

| 知识库用途 | 本机版本 | 论文/片段 |
| --- | --- | --- |
| 全局激活；RAG未指定版本时读取 | `semantic-mac-20261019` | 3 / 378 |
| 历史先导 | `arxiv-pilot-5-20261019` | 5 / 1019 |
| Agent/Auto未指定版本的实验基线 | `all-papers-8-20261020` | 8 / 1397 |
| 网页当前；通过`data/webui/library.json`独立选择 | `webui-72bf8b69e9cf45f28135637e5ead075c` | 9 / 1767 |
| QASPER独立评测库；未切换现有指针 | `qasper-test50-20261024` | 15 / 1612 |
| 10月25日新论文配对评测库；未激活 | `qasper-holdout-20261025` | 16 / 1459 |

旧版本和首次标题回退前的网页版本均保留。`activate`改变全局指针，不改变网页独立指针或Agent/Auto的默认八篇版本。[版本操作](docs/KNOWLEDGE_BASE_VERSIONS.md)

版本目录、指针、上传PDF、运行日志和`api.local.json`被Git忽略；本地提交不会把当前9篇网页库和私有配置同步到其他机器。原迁移用根目录数据按现有规则保留。不得覆盖知识库、旧实验或泄露密钥；跨设备复制配对资产后另行校验。公开仓库前的文件/许可审阅未在本轮执行。

## 6. 检索基线与验证口径

42道历史可答题、八篇库、候选120、最多两轮补查，Top-10/20独立运行；4道无Gold跳过。Top-10的Precision/nP/Recall/MAP/MRR为.1310/.6790/.7679/.4837/.5708，完整Gold入选28/42。Top-20的Recall约多4.37个百分点，未到预设5点门槛，默认保持10。[完整指标与来源](docs/PROJECT_METRICS.md)

这是指定Gold检索指标，不是回答准确率；nP不是全部上下文有用比例，附加原文不冒充同预算Recall提升。离线替身、已知题开发回归、真实入口运行、独立质量评测分别记录。冷启动与CPU预加载后耗时不混比，路径归因成本和实际去重请求不混加。

## 7. 文件导航与本轮整理

- [README](README.md)：网页和CLI入口、默认值与验证命令。
- [实验总览](docs/PROJECT_METRICS.md)：分版本质量、成本、检索、失败与结论。
- [网页说明](webui/README.md)、[代码阅读](docs/CODE_READING_GUIDE.md)、[Agent操作](docs/AGENT_REPLAY_GUIDE.md)、[文档导航](docs/README.md)。
- [本轮整理与文件核验](docs/maintenance/p4_closeout_20261024/report.md)：本轮没有新增付费评测；开始前4375份既有文件留哈希，原进度/量化文档逐字节归档。
- [实验原始索引](evaluation/results/README.md)、[历史归档](docs/history/README.md)：保留全部原始问题、Gold、请求、失败、成本和源码快照。
