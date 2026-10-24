# 辅助命令：读取私有配置对应服务的模型列表；列出 ID 不等于逐个验证生成能力。

"""Read available model IDs from the configured proxy; no generation request."""

from src.api_llm import list_models


def main():
    try:
        models = list_models()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
    print(f'可见模型：{len(models)} 个（尚未逐个测试生成能力）')
    for model in models:
        print(model)


if __name__ == '__main__':
    main()
