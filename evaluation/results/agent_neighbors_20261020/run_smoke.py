# P2.2 邻段工具的一次人工开发样例：只读既有库，不搜索或生成答案。
# 已有协议时拒绝重跑；恢复上下文直接看保存的 JSON。
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sys
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
if (OUTPUT / 'protocol.json').exists():
    raise SystemExit('已有本次协议；请直接查看已保存结果，不重复执行。')
sys.path.insert(0, str(ROOT))
network_attempts = []
tool_attempts = []


def deny_network(*args, **kwargs):
    network_attempts.append('blocked')
    raise AssertionError('本次读取禁止网络请求')


def deny_tool(*args, **kwargs):
    tool_attempts.append('blocked')
    raise AssertionError('本次读取禁止加载模型、推理或搜索')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (OUTPUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.create_connection = deny_network
from src import agent_tools as tools
from src.knowledge_base import load_knowledge_base

# 从上一步的真实搜索结果中，人工选择已经命中的 763；不运行新的搜索。
prior_path = ROOT / 'evaluation/results/agent_local_search_20261020/search_result.json'
prior = json.loads(prior_path.read_text(encoding='utf-8'))
anchor = next(item for item in prior['results'] if item['chunk_id'] == 763)
_, chunks, metadata = load_knowledge_base(ROOT / 'data/processed', tools.SEARCH_KB_VERSION)
assert anchor['kb_version'] == metadata['version']
assert all(anchor[key] == chunks[763][key] for key in chunks[763])
inputs = [Path(__file__).resolve(), ROOT / 'src/agent_tools.py',
          ROOT / 'src/knowledge_base.py', ROOT / 'tests/test_agent_tools.py', prior_path,
          Path(metadata['index_path']), Path(metadata['chunks_path']), Path(metadata['manifest_path'])]
hashes = {str(path.relative_to(ROOT)): digest(path) for path in inputs}
save('protocol.json', {
    'sample_type': 'manual_known_development_example', 'kb_version': metadata['version'],
    'chunk_id': 763, 'source': anchor['source'], 'window': 2,
    'expected_ids': [761, 762, 763, 764, 765], 'read_limit': 1,
    'search_limit': 0, 'model_inference_limit': 0, 'generation_api_limit': 0,
    'network_limit': 0, 'input_sha256': hashes,
})
for name in ('src/agent_tools.py', 'src/knowledge_base.py', 'tests/test_agent_tools.py'):
    target = OUTPUT / 'source_snapshot' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, target)

# 最小资源只有原文与版本元数据；阻断其余入口，证明无需模型权重或新检索。
with ExitStack() as guards:
    for name in ('load_search_resources', 'load_embedding_model', 'CrossEncoder',
                 'search_local_kb', 'retrieve', 'retrieve_bm25', 'rerank_results'):
        guards.enter_context(patch.object(tools, name, side_effect=deny_tool))
    result = tools.read_neighbors(763, {'chunks': chunks, 'knowledge_base': metadata},
                                  source=anchor['source'], window=2)
assert result['trace']['selected_ids'] == [761, 762, 763, 764, 765]
assert [item['offset'] for item in result['results']] == [-2, -1, 0, 1, 2]
for item in result['results']:
    assert all(item[key] == chunks[item['chunk_id']][key] for key in chunks[item['chunk_id']])
    assert item['source'] == anchor['source'] and item['kb_version'] == metadata['version']
assert all(digest(path) == hashes[str(path.relative_to(ROOT))] for path in inputs)
assert not network_attempts and not tool_attempts
save('neighbor_result.json', result)
save('smoke_summary.json', {
    'successful': True, 'manual_read_calls': 1, 'agent_actions_executed': 0,
    'search_calls': 0, 'model_loads': 0, 'model_inference_calls': 0, 'generation_api_calls': 0,
    'network_attempts': len(network_attempts), 'forbidden_tool_attempts': len(tool_attempts),
    'selected_ids': result['trace']['selected_ids'], 'returned_count': len(result['results']),
    'read_chars': result['trace']['read_chars'], 'elapsed_seconds': result['trace']['elapsed_seconds'],
    'raw_identity_matches': True, 'inputs_unchanged': True,
    'answer_generation_or_semantic_acceptance': False,
})
print('一次人工邻段读取通过；原文身份一致；模型/检索/生成API/网络调用均0。')
