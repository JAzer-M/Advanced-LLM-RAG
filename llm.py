import torch
from transformers import AutoProcessor, AutoModelForMultimodalLM
from functools import lru_cache

@lru_cache(maxsize = 1)
def load_llm():
    model_name = "Qwen/Qwen3.5-2B"

    processor = AutoProcessor.from_pretrained(
        model_name,
        local_files_only=True
    )

    model = AutoModelForMultimodalLM.from_pretrained(
        model_name,
        dtype = torch.bfloat16,
        device_map = "auto",
        local_files_only=True
    )

    model.eval()

    return processor, model

def generate_answer(prompt):
    # 指定模型
    processor, model = load_llm()

    # 构建对话信息
    message = [
        {
            "role": "user",
            "content":[
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }
    ]

    # 转换模型输入
    inputs = processor.apply_chat_template(
        message,
        tokenize = True,
        add_generation_prompt = True,
        return_dict = True,
        return_tensors = "pt"
    ).to(model.device)

    # 使用LLM生成答案
    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens = 512,
            do_sample = False
        )

    # 提取新生成的token
    generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
    print("Generated Token Count:", generated_ids.shape[0])

    # Decode
    answer = processor.decode(
        generated_ids,
        skip_special_tokens = True,
    )

    return answer