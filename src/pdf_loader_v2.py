import re

def extract_text_blocks(page):
    text_blocks = []

    for i, block in enumerate(page.get_text("blocks")):

        # 只保留文本块
        if block[6] != 0:
            continue

        text = block[4].strip()

        if not text:
            continue

        # 初步识别 Block 类型
        block_type = "text"

        if re.match(r"^Table\s+\d+\s*:", text, re.IGNORECASE):
            block_type = "table_candidate"

        elif re.match(
                r"^(?:Figure|Fig\.?)\s*\d+\s*[:.]",
                text,
                re.IGNORECASE
        ):
            block_type = "figure_candidate"

        text_blocks.append({
            "block_id": i,
            "page": page.number + 1,
            "bbox": tuple(block[:4]),
            "text": text,
            "block_type": block_type,
        })

    return text_blocks
