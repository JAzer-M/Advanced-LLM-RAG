"""OpenAI-compatible proxy client shared by all active LLM calls."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SETTINGS_PATH = Path(__file__).resolve().parents[1] / 'api.local.json'


class IncompleteResponseError(RuntimeError):
    """Keep partial output and usage available to the evaluation audit."""

    def __init__(self, response):
        self.response = response
        super().__init__(
            f"API 回答未完成，finish_reason={response['finish_reason']}。未自动重试。")


def load_settings():
    return json.loads(SETTINGS_PATH.read_text(encoding='utf-8')) if SETTINGS_PATH.is_file() else {}


def _request(path, payload=None):
    settings = load_settings()
    key = os.environ.get('RAG_API_KEY') or settings.get('api_key', '')
    if not key.strip():
        raise RuntimeError('请在 api.local.json 填写 api_key，或设置 RAG_API_KEY。')
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else None
    request = Request(settings['base_url'].rstrip('/') + path, data=data,
                      headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=90 if payload is not None else 10) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f'反代 API 请求失败：HTTP {exc.code}。未自动重试。') from None
    except (URLError, TimeoutError):
        raise RuntimeError('反代 API 连接失败或超时；未自动重试。') from None


def list_models():
    return [item['id'] for item in _request('/models').get('data', [])]


def chat_completion(prompt, model=None, options=None):
    settings = load_settings()
    model = model or settings.get('model')
    if not model:
        raise RuntimeError('尚未选择 API model。')
    payload = {'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'stream': False}
    payload.update(settings.get('chat_options', {}) if options is None else options)
    if 'max_tokens' not in payload and 'max_completion_tokens' not in payload:
        payload['max_tokens'] = 512
    response = _request('/chat/completions', payload)
    choice = response['choices'][0]
    answer = choice['message'].get('content')
    result = {'answer': answer, 'requested_model': model, 'reported_model': response.get('model'),
              'usage': response.get('usage'), 'finish_reason': choice.get('finish_reason'),
              'request_parameters': {k: v for k, v in payload.items() if k != 'messages'}}
    # 当前调用只用于文本回答，只有 stop 表示生成正常结束。
    if result['finish_reason'] != 'stop':
        raise IncompleteResponseError(result)
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError(f"API 未返回正文，finish_reason={choice.get('finish_reason')}。未自动重试。")
    return result


def generate_final_answer(prompt):
    return chat_completion(prompt)['answer']
