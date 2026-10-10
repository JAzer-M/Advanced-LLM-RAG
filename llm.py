import torch
from transformers import AutoProcessor, AutoModelForMultimodalLM

# 指定模型
model_name = "Qwen/Qwen3.5-2B"

processor = AutoProcessor.from_pretrained(
    model_name,
    local_files_only=True
)

# 加载预训练模型
model = AutoModelForMultimodalLM.from_pretrained(
    model_name,
    dtype = torch.bfloat16,
    device_map = "auto",
    local_files_only=True
)

# 设置推理模式
model.eval()

# 查看结果
print(model.device)
print(model.dtype)

# 设置用户问题
message = [
    {
        "role": "user",
        "content":[
            {
                "type": "text",
                "text": "Why does VGG use small 3*3 concolutional filters?",
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
        max_new_tokens = 128,
        do_sample = False
    )

# 提取新生成的token
generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]

# 将token IDs解码成文本
answer = processor.decode(
    generated_ids,
    skip_special_tokens = True,
)

print("\nGenerated answer:")
print(answer)