# 五篇 arXiv 论文：下载与 Mac 先导实验

本文保留首次先导实验的原始结果；随后完成的分解/选证据修复和七题评估见[后续 evaluation 日志](DECOMPOSITION_EVALUATION_2026-10-19.md)。

2026-10-19。已从官方 arXiv 下载五篇固定版本的 PDF，在本机 CPU 构建独立知识库并完成检索、三题真实问答。运行的是本项目现有 RAG 程序；五篇方法是知识库内容，并未实现或测速这五种算法。

实验版本为 `arxiv-pilot-5-20261019`，共 **88 页、1,019 个片段、384 维**。默认仍为三篇论文的 `semantic-mac-20261019`（378 条）；原有 18 个基线文件逐字节未改，含旧版本、当前指针、原始数据和 API 私有配置。

## 论文与本地数据

| 论文 | 固定版本与官方来源 | PDF 页数 | 片段数 |
| --- | --- | --- | --- |
| Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks | [2005.11401v4](https://arxiv.org/abs/2005.11401v4) | 19 | 210 |
| Dense Passage Retrieval for Open-Domain Question Answering | [2004.04906v3](https://arxiv.org/abs/2004.04906v3) | 13 | 168 |
| ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT | [2004.12832v2](https://arxiv.org/abs/2004.12832v2) | 10 | 170 |
| Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection | [2310.11511v1](https://arxiv.org/abs/2310.11511v1) | 30 | 291 |
| Corrective Retrieval Augmented Generation | [2401.15884v3](https://arxiv.org/abs/2401.15884v3) | 16 | 180 |

- PDF：`data/raw/arxiv-pilot-20261019/`，以带版本号的 ID 命名；下载状态与 SHA-256 为同目录 `downloads.json`。
- [论文清单](../data/arxiv_pilot_20261019.json)：官方 Atom 元数据、作者、版本、日期、来源、另行核对的许可与选文用途。
- 索引：`data/processed/versions/arxiv-pilot-5-20261019/`，含 FAISS、chunks、配对 manifest，以及论文清单和 PDF 哈希。
- [选文与题目依据](ARXIV_PILOT_SELECTION_2026-10-19.md)：使用 Matt Pocock research 技能核对官方来源；手工先导样本，不是随机抽样。

新 PDF 和版本目录沿用已有 Git 忽略规则，保留在本机；本轮没有提交、推送或自动同步到 Windows。公开复现入口是元数据清单和下载脚本，全文再发布依据各篇许可。[arXiv 使用说明](https://info.arxiv.org/help/api/tou.html)

## 本次实现与导入检查

1. `download_arxiv_papers.py`：按固定版本清单串行下载，保守间隔至少 3.1 秒；有限重试、临时文件校验后发布；记录完成/失败。重跑先验证已有 SHA-256，跳过完成文件，已改动文件拒绝覆盖。这里的恢复是按文件重跑，未做字节断点续传。
2. `build_semantic_index.py`：增加显式双栏文件参数和可选论文清单。构建前核对清单与 PDF 集合，补齐 PDF 内缺失的标题，并把来源和哈希写进版本 manifest。保留已有分块、Embedding 和索引算法。
3. `evaluation/run_arxiv_pilot.py`：复用真实检索函数，模型在一轮中复用；记录各阶段 Gold 排名及 Top-10。完全离线，不调用分解或生成 API。
4. `evaluation/run_answer_evaluation.py`：增加 `--questions`，可用新题集及既有 API 审计入口；原六题仍为默认，未知/重复题目 ID 拒绝运行。

实际下载五篇均成功；立即重复运行时五篇全部 `skipped_verified`，没有再次下载。另用真实 PDF 字节、模拟网络中断检查：完成文件保留，失败有记录、临时文件移除；重跑只请求失败的一篇，再跑请求数为零；修改本地 PDF 后校验报错且不覆盖。模拟检查不冒充真实 arXiv 故障恢复经历。[下载记录](../evaluation/results/arxiv_pilot_20261019/download_first.json)、[重复运行](../evaluation/results/arxiv_pilot_20261019/download_repeat.json)、[模拟恢复检查](../evaluation/results/arxiv_pilot_20261019/download_recovery_test.json)。

88 页均能提取文本，且均有分块，所有片段页码合法。抽看五道单篇题的原始 PDF 页面，另核对 RAG 第 18 页附录；DPR/ColBERT/CRAG 使用显式双栏，RAG/Self-RAG 使用单栏。Self-RAG Table 1 的四类标签与定义保留在同一片段。只抽查了 6 页，跨页断句、连字符、公式与复杂表格仍受现有解析器限制，不宣称全量无损。[解析检查](../evaluation/results/arxiv_pilot_20261019/pdf_quality.json)。

## 检索结果：指定段落与有效证据分别检查

先固定 [7 道中文题与 Gold](../evaluation/arxiv_pilot_questions.json)，再运行原问题 Dense/BM25 各 60 → RRF 60 → BGE Top-10；不进行 API 分解。六道可答题的预设 Gold 均能在库中定位，说明这批关键文字没有在入库时丢失。

**严格指定 Gold 段落全部进入 Top-10：中文 2/6，后补英文表达对照 4/6。** 英文对照在看到中文结果后用于诊断，保留相同 Gold、候选预算和算法，未在问题中加入答案；它不是独立留出集。中文原始 Gold 和结果没有为提高分数改写。单个指定段落漏检不等于没有其他直接证据，人工检查如下。

| 中文题 | 实际 Top-10 中的证据 | 人工结论 |
| --- | --- | --- |
| p1 RAG 生成器及参数 | 第 18 页参数附录，chunk 542，Rank 9 | 有依据：BART-large、406M；预设第 3 页正文写 400M，回答应区分正文概述与附录数值 |
| p2 DPR 相似度 | 第 3 页，chunk 28，Rank 1 | 点积有直接支持 |
| p3 ColBERT MaxSim | 第 2 页 chunk 195，以及第 4/5 页说明 | 每查询 token 取最大匹配后求和有直接支持；预设片段 219 未入 Top-10 |
| p4 Self-RAG reflection tokens | 第 4 页 Table 1，chunk 587，Rank 2 | 四类 token 与职责齐备 |
| p5 CRAG 三类判断 | 第 4 页 Figure 2 图注，chunk 877，Rank 1 | 三类判断有直接支持；预设第 3 页段落未入 Top-10 |
| p6 DPR / ColBERT 比较 | DPR 点积、ColBERT 概述及乱序公式 | 部分支持；缺少清晰的 ColBERT MaxSim 求和说明 |
| p7 五种方法在这台 Mac 的毫秒数 | 无本机实测 Gold | 应说明证据不足，不能据其他硬件实验数字排名 |

因此本批五道单篇题均找到可用证据，跨篇题证据不足。这个判断只针对当前小样本，不能换算为总体准确率。英文对照使 p1、p5 指定段落进入 Top-10，但没有解决跨篇覆盖；是否增加查询增强需再单独验证，现有 rewrite/HyDE 默认仍关闭。

原始结果：[中文检索](../evaluation/results/arxiv_pilot_20261019/retrieval.md)、[各阶段排名与全文](../evaluation/results/arxiv_pilot_20261019/retrieval.json)、[英文对照](../evaluation/results/arxiv_pilot_20261019/english_control/retrieval.md)、[人工核对](../evaluation/results/arxiv_pilot_20261019/manual_review.json)。

## 三道真实主流程问答

选择在原流程中运行 p3（单篇）、p6（跨篇）、p7（库外本机测量）。均使用新知识库的真实检索和当前 API；reference answer / Gold 未传给生成模型。

| 题目 | 结果 | 需要保留的问题 |
| --- | --- | --- |
| [p3 原始答案与引用](../evaluation/results/arxiv_pilot_20261019/answers/p3.md) | MaxSim 最大匹配与求和回答完整，引用 1/3/7 有原文支持 | 指定 Gold 漏检，但有替代证据 |
| [p6 原始答案与引用](../evaluation/results/arxiv_pilot_20261019/answers/p6.md) | DPR 部分有依据，ColBERT 具体打分说明不完整，答案承认缺证据 | 分解 API 实际返回 4 个子问题，超过当前 2～3 个限制，被校验器静默回退为“不分解”；同时缺少关键说明，公式抽取乱序 |
| [p7 原始答案与引用](../evaluation/results/arxiv_pilot_20261019/answers/p7.md) | 正确说明没有本机实测数据，未编造五种方法的 Mac 排名和毫秒数 | 答复切为英文，并增加其他硬件实验数字，语言与简洁性仍需改进 |

三题均正常完成，引用编号结构检查 3/3，通过不等于内容完整。人工结论为：单篇回答完整、跨篇部分完成、缺失证据题拒答正确但有表达问题。本轮保留原流程缺陷作为基线，没有同时修改分解规则或生成提示来改变实验结果。

实际生成 API **6 次**：三次分解、三次回答，全部 `finish_reason=stop`，未触发引用修复。代理返回输入 **6,586**、输出 **870**、合计 **7,456 token**。未根据代理自定义 credit 字段推断人民币费用。[调用审计](../evaluation/results/arxiv_pilot_20261019/answers/collection.json)、[总核验](../evaluation/results/arxiv_pilot_20261019/verification.json)。

## 复现与继续使用

在项目根目录使用现有 `.venv`。Mac 的 Python 默认证书链缺失，首次 urllib 元数据连接失败；元数据改用校验证书的系统 curl 获取，PDF 下载进程显式指定系统 CA，未关闭 TLS 验证、未修改全局证书配置。

```bash
SSL_CERT_FILE=/etc/ssl/cert.pem .venv/bin/python download_arxiv_papers.py \
  --manifest data/arxiv_pilot_20261019.json \
  --output-dir data/raw/arxiv-pilot-20261019
```

Mac 构建与检索使用已验证的线程限制；默认线程崩溃根因仍未解决。以下新建版本名必须尚不存在；本次已建好的版本可直接读取。

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -u -c "import runpy, torch; torch.set_num_threads(1); torch.set_num_interop_threads(1); runpy.run_path('build_semantic_index.py', run_name='__main__')" \
  --version arxiv-pilot-5-new-build \
  --raw-dir data/raw/arxiv-pilot-20261019 \
  --two-column-files 2004.04906v3.pdf 2004.12832v2.pdf 2401.15884v3.pdf \
  --paper-manifest data/arxiv_pilot_20261019.json
```

直接用已建好的五篇版本问一个问题（会调用反代 API）：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -c "import torch; torch.set_num_threads(1); torch.set_num_interop_threads(1); import main; main.main('ColBERT 的 MaxSim 如何计算文档得分？', kb_version='arxiv-pilot-5-20261019')"
```

完整实验的参数、版本、环境与代码/数据哈希保存在 [protocol.json](../evaluation/results/arxiv_pilot_20261019/protocol.json) 和各结果 JSON。英文对照第一次因新增脚本把相对输入路径直接转项目相对路径而在出题前退出；已只修正审计路径标准化，保留失败日志后重跑成功，无额外生成 API 调用。中文首次结果保留其原始代码哈希。

既有 **25 个回归测试通过**，新题集已实际跑通答案收集入口；下载中断/篡改防覆盖另有上述模拟检查。尚未实现主题自动筛选、跨版本内容去重与稳定片段 ID、完整导入生命周期或 Agent 闭环。下一步优先用本次保存的四子问题响应修复并测试分解校验策略，再处理中文输出与跨论文证据覆盖，随后扩评测和语料规模。
