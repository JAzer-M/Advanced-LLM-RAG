# 在 PyCharm 中运行 API 版 RAG

## 先理解调用关系

PyCharm 负责启动 Python。API 请求由项目代码发出，因此不需要在 PyCharm 的 AI 插件里选择模型，也不需要让 PyCharm 本身登录模型账号。

当前路径是：

```text
在 PyCharm 运行 main.py
  → 问题分解 / 最终回答 / 必要时一次引用修复
  → llm.generate_answer 或 src.api_llm.generate_final_answer
  → src.api_llm.chat_completion
  → HTTP POST http://127.0.0.1:7863/v1/chat/completions
  → 本机反代转发给模型
  → 取响应 choices[0].message.content
```

同一个 API 连接现在用于所有启用的生成调用。检索仍使用本地 embedding、BM25、FAISS 和 CPU 重排；停用本地生成模型不等于删除这些检索模型，也不意味着可以卸载它们依赖的 PyTorch。

## 三个连接字段

在项目根目录的 `api.local.json` 中：

本项目已经配置好。新项目可把 `api.example.json` 复制成 `api.local.json` 后填写 Key；已有配置不必重新复制。

| 字段 | 含义 | 本项目当前设置 |
|---|---|---|
| base_url | 反代接口的根地址 | http://127.0.0.1:7863/v1 |
| api_key | 反代的访问凭证 | 保留你已在本地填写的值 |
| model | 反代认得的模型 ID，必须精确一致 | cn:deepseek-v4.1-flash |

这三个值类似其他 Agent 软件里的 URL、Key、模型选择，只是保存在 Python 项目的配置文件中。代码会自动在 base_url 后拼接 `/chat/completions`；不要把完整生成路径再填进 base_url。

当前 `chat_options` 为：

```json
{
  "thinking": {"type": "disabled"},
  "temperature": 0,
  "max_tokens": 4096
}
```

2026-10-18 按用户要求改为 DeepSeek v4.1 Flash，移除 Kimi 专属的 reasoning_effort / max_completion_tokens，采用关闭思考的请求配置。DeepSeek 官方支持通过 thinking.type 切换思考模式，见 [Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/)。反代可能转换参数；随后本轮已实际跑通六题主流程与固定证据检查，兼容性和回答限制见 [2026-10-18 调试日志](DEEPSEEK_V41_DEBUG_LOG_2026-10-18.md)。

4096 是单次输出上限，不表示每次都消耗 4096，也不表示上下文只能有 4096 token。关闭思考沿用此前 DeepSeek 对比的设置；本轮只检查该配置下的 v4.1，没有比较各推理档位。历史 Kimi 检查使用 low reasoning effort，与当前配置分开记录。

## 在 PyCharm 里怎么运行

1. 先启动你的本机反代服务，保持 7863 端口可用。`127.0.0.1` 指运行 Python 的这台电脑；换到远程主机或容器后需重新确认地址。
2. 使用 PyCharm 打开 `C:\Users\J\Desktop\Advanced-LLM-RAG`。
3. 项目 Python Interpreter 选择现有 `.venv\Scripts\python.exe`。API 客户端使用标准库，不需要额外安装 openai SDK。
4. 右键 `main.py` → Run。也可以在 Run → Edit Configurations 中指定 Script path 为 main.py、Working directory 为项目根目录、Parameters 留空。
5. 在 Run 控制台输入问题，观察启动行 `LLM: proxy API | Model: cn:deepseek-v4.1-flash`，随后查看检索、证据、引用检查与答案。

不需要先运行 llm.py，也不需要每次手工发送 HTTP 请求。llm.py 是供其他模块导入的公共生成入口。

如果 Hugging Face 模型已缓存，为避免检索模型联网探测，在上述运行配置的 Environment variables 中可加入：

```text
HF_HUB_OFFLINE=1;TRANSFORMERS_OFFLINE=1
```

它们只影响 Hugging Face 模型加载，不会关闭 urllib 发给本地反代的 API 请求。如果检索模型尚未下载，首次准备缓存时不要强制离线。

## Key 的读取和保存

当前代码按项目文件位置读取 `api.local.json`，不依赖你在哪个终端设置变量。配置在本地修改并保存即可生效；Key 已加入 Git 忽略，不要复制到报告或聊天里。

代码也支持环境变量 `RAG_API_KEY`，其优先级高于 JSON。若采用这种方式，应在 PyCharm 的运行配置里设置。另开 PowerShell 设置 `$env:RAG_API_KEY`，不会自动改变已经运行的 PyCharm 进程环境。

Git 忽略只是避免正常提交，并不是对本地文件加密。分享项目时提供空白模板，勿附上真实配置文件。

## 代码实际做了什么

`src/api_llm.py` 读取配置后构造 JSON：

```python
payload = {
    "model": model,
    "messages": [{"role": "user", "content": prompt}],
    "stream": False,
    **chat_options,
}
```

请求头用 `Authorization: Bearer <本地读取的Key>` 认证，正文通过 POST 发给反代。返回的 `content` 才是答案；思考内容不打印或保存为用户答案。协议结构参考 [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)。

调用封装后的代码只需要：

```python
from llm import generate_answer

answer = generate_answer(prompt)
```

所以换模型主要是更改 model 和该模型支持的参数，不是更换 PyCharm；参数不能在不同模型之间照搬。原本 Qwen 的加载实现已从当前代码环境移除；清理前代码有恢复快照，见清理日志。

## 遇到错误看哪里

- 401：检查本地 Key，尤其是否有旧的 RAG_API_KEY 环境变量覆盖 JSON。
- 400：核对模型 ID 和模型专属参数。
- 503：可能是反代或上游暂时不可用；这不等同于证据解析错误。历史 Kimi 初次请求遇到过 503，独立最小请求随后成功。程序不会无限重试。
- 连接失败：先检查反代是否启动、端口和地址是否一致。
- 空正文 / length：检查模型的思考与输出预算；不要把未完成的答案标为通过。

启动时仍可能出现检索模型的 Loading weights；这属于本地 embedding/重排权重，不代表又启动了历史 Qwen 生成模型。

检查模型名单可运行 `list_api_models.py`，它只列模型，不生成答案。日常问答只运行 main.py 即可；全面检查脚本会多次调用 API、消耗反代额度，不必每次使用都运行。
