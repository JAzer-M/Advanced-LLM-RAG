# P2.2 第二步：读取邻段工具验收

日期：2026-10-20（Asia/Shanghai）。本轮按用户授权实现邻段读取，沿用普通函数、字典和列表；未推进工具执行分派或反馈循环。

## 实现与用途

在[src/agent_tools.py](../../../src/agent_tools.py)新增`read_neighbors(chunk_id, resources, source, window=1)`，附中文用途、校验与切片注释。原`load_search_resources()`和`search_local_kb()`函数AST完全一致，既有搜索测试保留。

1. 校验当前库内整数ID、中心段的精确论文文件名，以及0～2的整数window；拒绝负数、bool、浮点数和错误来源。
2. 从已加载chunks筛出同一论文，保留入库顺序，再定位中心。避免全库ID直接加减时跨论文或遇到来源交错。
3. 返回中心段及前后各window段，首尾自动截断。默认最多3段，最大5段；window=0只返回中心。
4. 复制原文与元数据，增加kb_version、offset。offset=0表示中心，负数为前文，正数为后文；trace记录窗口、ID、总字符数和耗时。

检索把长文切成片段后，可能命中主题背景，但定义、条件、评价判据在相邻段中。该工具按文档顺序展开附近原文，供之后的证据检查使用。它不加载模型、不搜索、不重排、不生成回答；只需同一知识库版本中经加载器校验的chunks和knowledge_base。ID只在所属版本内有效，应复用产生搜索结果的资源。

这里的邻段依据已保存分块的顺序，允许跨同篇论文的页或章节边界；它无法恢复解析或分块时遗漏的内容。

```python
from src.agent_tools import read_neighbors

# result、resources沿用同一进程里的search_local_kb调用。
hit = result['results'][0]
nearby = read_neighbors(hit['chunk_id'], resources, source=hit['source'])
for item in nearby['results']:
    print(item['offset'], item['chunk_id'], item['page'], item['text'])
```

## 验证结果

新增10项测试，**全部142项unittest通过**，失败、错误、跳过均0，网络请求0。覆盖同篇原文顺序、交错来源、论文边界、单段文档、窗口0/2、错误参数、原文和元数据保留、输入不变，以及仅用最小资源读取。见[tests.json](tests.json)和[tests.log](tests.log)。

真实检查只进行一次人工邻段读取，中心763来自[上一步真实搜索](../agent_local_search_20261020/search_result.json)，论文为`2005.11401v4.pdf`。这是已知开发样例，人工指定window=2；运行前冻结[协议](protocol.json)，不读取Gold或旧答案驱动本次执行，也不重新搜索。

| chunk ID | offset | PDF页码 | 内容线索 |
| --- | --- | --- | --- |
| 761 | -2 | 4 | Wikipedia分块、检索索引与训练检索 |
| 762 | -1 | 4 | 训练和测试的检索k设置 |
| 763 | 0 | 4 | 开放域QA任务、训练目标及对比方法 |
| 764 | 1 | 4 | 闭卷QA对比与评测数据集 |
| 765 | 2 | 4 | 数据划分及Exact Match（EM）评价说明 |

返回5段、共1643字符，ID/来源/页码/标题/章节/正文与配对库逐字段一致，offset为[-2,-1,0,1,2]。纯读取实测0.000055秒；此值不含库加载和模块导入，不代表完整RAG延迟或服务性能。

模型加载、模型推理、重新搜索、生成API、网络请求均0；执行时阻断网络及模型/检索入口，没有触发阻断。Agent执行行动仍为0，本轮为普通函数的手动调用。完整[原文结果](neighbor_result.json)、[统计](smoke_summary.json)、[运行脚本](run_smoke.py)及`source_snapshot/`保留；脚本已有协议时拒绝自动重跑。

该样例展示附近原文可以展开，不代表Agent自主选择了中心或窗口，也没有检查h10最终答案、补查后的语义支持或完整Agent收益。

## 修改范围与资产核对

核对2207项原有文件，仅修改`src/agent_tools.py`、`tests/test_agent_tools.py`、README、PROGRESS和代码阅读说明。2114项旧数据、实验结果与历史文件哈希一致；`agent.py`、`main.py`及原搜索函数保留。48个维护中的Python文件与新验收驱动通过纯编译检查。知识库、激活指针、桌面纯路线图及`docs/PROJECT_WORKFLOW.md`均未改变。见[verification.json](verification.json)。

本轮未新增运行依赖、重建索引、调用付费API、提交或推送。后续先由用户阅读代码，再按明确指示处理执行分派与反馈循环。
