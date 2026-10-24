# 把 PDF 转成带 source/page/title/section 的 document 列表，供后续分块使用。
# 一个 document 是同页连续章节文本，不必等于整页；page 从 1 开始。
# 双栏顺序和章节识别是显式开关/启发式规则，不能当作通用版式恢复器。

import pymupdf
import re
from pathlib import Path
from statistics import median

# 逐页提取并按连续 section 分组；current_section 可从上一页延续。
def load_pdf(pdf_path, two_columns = False):

    documents = []

    with pymupdf.open(pdf_path) as pdf:

        metadata = pdf.metadata

        title = (metadata.get("title") or "").strip()

        if not title:
            title = Path(pdf_path).stem

        current_section = None

        for page_number, page in enumerate(pdf, start=1):

            # 提取文本行
            lines = extract_lines(page, two_columns = two_columns)

            # 检测章节标题
            sections = detect_sections(lines)

            # 为每一行分配 Section
            assign_lines, current_section = assign_sections(
                lines,
                sections,
                current_section
            )

            # 根据section将连续文本分组
            groups = []

            for line in assign_lines:
                section = line["section"]

                if not groups or groups[-1]["section"] != section:

                    groups.append({
                        "section": section,
                        "texts": []
                    })

                groups[-1]["texts"].append(line["text"])

            # 每个分组生成一个document
            for group in groups:

                text = clean_text("\n".join(group["texts"]))

                if not text:
                    continue

                document = {
                    "text": text,
                    "page": page_number,
                    "source": Path(pdf_path).name,
                    "title": title,
                    "section": group["section"]
                }

                documents.append(document)

    return documents

# 只遍历指定目录本层的 *.pdf；子目录中的论文需另行指定目录。
def load_pdfs(folder_path, two_columns_files = None):
    two_columns_files = set(two_columns_files or [])

    all_documents = []

    pdf_files = sorted(Path(folder_path).glob("*.pdf"))

    for pdf_path in pdf_files:

        documents = load_pdf(
            pdf_path,
            two_columns = pdf_path.name in two_columns_files
        )

        all_documents.extend(documents)

    return all_documents

# 保留字形/字号/坐标；双栏开关打开时按左栏再右栏排序。
def extract_lines(page, two_columns = False):

    lines = []

    blocks = page.get_text("dict")["blocks"]

    for block in blocks:

        if "lines" not in block:
            continue

        for line in block["lines"]:
            text = ""
            fonts = []
            sizes = []

            for span in line["spans"]:
                text += span["text"]
                fonts.append(span["font"])
                sizes.append(span["size"])

            text = text.strip()

            if text:
                lines.append(
                    {
                        "text": text,
                        "fonts": fonts,
                        "sizes": sizes,
                        "bbox": line["bbox"]
                    }
                )

    if two_columns:

        column_boundary = page.rect.width * 0.45

        lines.sort(
            key = lambda line: (
                line["bbox"][0] >= column_boundary,
                line["bbox"][1],
                line["bbox"][0]
            )
        )

    return lines

# 结合编号、字号和加粗猜测章节标题，排除表/图标题等常见干扰。
def detect_sections(lines):

    sections = []

    # 定义章节编号格式
    number = r"[1-9]\d?(?:\.\d{1,2}){0,3}"

    number_pattern = re.compile(
        rf"^{number}\.?$"
    )

    full_pattern = re.compile(
        rf"^({number})\.?\s+([A-Za-z].*)$"
    )

    # 估计当前页面的正文字体大小
    body_sizes = [
        max(line["sizes"])
        for line in lines
        if len(line["text"]) >= 50 and line["sizes"]
    ]

    body_size = median(body_sizes) if body_sizes else 10.0

    # 判断字体是否加粗
    def is_bold(line):

        return any(
            "bold" in font.lower() or "medi" in font.lower()
            for font in line["fonts"]
        )

    # 判断文本是否具备标题特征
    def is_heading_title(text):
        if not re.match(r"^[A-Za-z]", text):
            return False

        if len(text) >= 80:
            return False

        if re.match(r"^(Table|Figure|Fig\.)\b", text, re.I):
            return False

        return True

    # 遍历文本行
    for i, current in enumerate(lines):

        text = current["text"].strip()

        if len(text) > 100 or "|" in text:
            continue

        # 过滤字号明显小于正文的文本
        if(
            current["sizes"]
            and max(current["sizes"]) < body_size * 0.85
        ):
            continue

        # 情况A: 编号和标题在同一行
        match = full_pattern.match(text)

        if match:
            heading_title = match.group(2).strip()

            enlarged = (
                bool(current["sizes"])
                and max(current["sizes"]) >= body_size + 1
            )

            if(
                is_heading_title(heading_title)
                and (
                    is_bold(current)
                    or heading_title.isupper()
                    or enlarged
                )
            ):
                sections.append({
                    "text": text,
                    "line_index": i
                })

            continue

        # 情况B: 编号和标题分布在两行
        if number_pattern.fullmatch(text):

            if i  + 1 >= len(lines):
                continue

            next_line = lines[i + 1]

            heading_title = next_line["text"].strip()

            # 获取当前编号和下一行标题的坐标
            current_x, current_y = current["bbox"][:2]
            next_x, next_y = next_line["bbox"][:2]

            # 判断两行在页面上是否足够接近
            spatially_adjacent = (
                abs(next_x - current_x) <= 6 * body_size
                and abs(next_y - current_y) <= 2 * body_size
            )

            if(
                spatially_adjacent
                and is_heading_title(heading_title)
                and (
                    heading_title.isupper()
                    or is_bold(next_line)
                )
            ):

                heading = text + " " + heading_title

                sections.append({
                    "text": heading,
                    "line_index": i
                })

    return sections

# 遇到新标题才更新当前章节，其余行沿用前一个章节标签。
def assign_sections(lines, sections, current_section = None):

    sections_lines = {
        section["line_index"]: section["text"]
        for section in sections
    }

    assign_lines = []

    for index, line in enumerate(lines):

        if index in sections_lines:

            current_section = sections_lines[index]

        assign_lines.append(
            {
                "text": line["text"],
                "section": current_section
            }
        )

    return assign_lines, current_section

# 仅删除空行和已知页眉，当前没有完整的表格、公式或通用噪声清洗。
def clean_text(text):

    lines = text.splitlines()

    cleaned_lines = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # 删除页眉
        if "COMMUNICATION OF THE ACM" in line:
            continue

        if "JUNE 2017" in line:
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)
