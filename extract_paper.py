#!"F:/Anaconda3/space/envs/paper_reader/python.exe"
"""
extract_paper.py — 从学术论文 PDF 中提取关键章节文字。

用法:
    python extract_paper.py input.pdf output.txt

依赖:
    pip install pymupdf
"""

import sys
import re
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF


# ── 配置 ──────────────────────────────────────────────────────────────

# 页眉/页脚裁剪区域（占页面高度的比例）
HEADER_RATIO = 0.12   # 页面顶部 12%
FOOTER_RATIO = 0.10   # 页面底部 10%

# 目标章节的正则（按在论文中的典型出现顺序排列）
# 每个章节有一组匹配模式，命中任一即视为该章节标题
SECTION_PATTERNS = [
    ("abstract", [
        r"^\s*abstract\s*$",
    ]),
    ("introduction", [
        r"^\s*(I\.|1[\.\s])?\s*introduction\s*$",
    ]),
    ("method", [
        r"^\s*(II\.?|III\.?|IV\.?|2[\.\s]|3[\.\s]|4[\.\s])\s*(method|methodology|approach|our\s+approach|proposed\s+method|model\s+architecture|framework)\s*$",
        r"^\s*(method|methodology|approach|our\s+approach|proposed\s+method)\s*$",
        # 兜底：Introduction 之后、Experiments 之前的编号章节（排除 Related Work / Background 等）
        r"^\s*(III\.?|IV\.?|3[\.\s]|4[\.\s])\s+(?!related\s|background\s|preliminar|problem\s+(statement|formulation)|dataset|experiment|evaluation|result|conclusion|discussion)[A-Z][a-zA-Z\s\-]+$",
    ]),
    ("experiments", [
        r"^\s*(III\.?|IV\.?|V\.?|VI\.?|3[\.\s]|4[\.\s]|5[\.\s]|6[\.\s])\s*(experiments?|experimental\s+(results|evaluation|setup)|evaluation|results?|performance)\s*$",
        r"^\s*(experiments?|experimental\s+(results|evaluation|setup)|evaluation)\s*$",
    ]),
    ("conclusion", [
        r"^\s*(V\.?|VI\.?|VII\.?|VIII\.?|5[\.\s]|6[\.\s]|7[\.\s]|8[\.\s])\s*(conclusion|discussion|summary|concluding\s+remarks)\s*$",
        r"^\s*(conclusion|discussion|summary|concluding\s+remarks)\s*$",
    ]),
]

# 参考文献章节的正则（从这里开始截断）
REF_PATTERNS = [
    r"^\s*references?\s*$",
    r"^\s*bibliography\s*$",
    r"^\s*R\s*E\s*F\s*E\s*R\s*E\s*N\s*C\s*E\s*S\s*$",
]

# 页眉/页脚中常见的噪声行
NOISE_PATTERNS = [
    r"^\s*\d+\s*$",                          # 纯页码
    r"^\s*\d+\s*/\s*\d+\s*$",                # "1 / 12"
    r"^©\s*\d{4}",                            # 版权声明
    r"^\s*arXiv:\d{4}\.\d{4,}(v\d+)?\s*$",   # arXiv ID
    r"^\s*Preprint",                          # Preprint 标记
    r"^\s*submitted\s+to\s+",                # 投稿标记
]


# ── 工具函数 ──────────────────────────────────────────────────────────

def page_y(page, ratio):
    """返回页面中 ratio 比例处对应的 y 坐标。"""
    _, _, _, height = page.rect
    return height * ratio


def is_noise(text):
    """判断单行文本是否为噪声（页码、版权声明等）。"""
    for pat in NOISE_PATTERNS:
        if re.match(pat, text, re.IGNORECASE):
            return True
    return False


def normalise(s):
    """归一化字符串：去多余空白，小写。"""
    return " ".join(s.split()).lower()


# ── 核心逻辑 ──────────────────────────────────────────────────────────

def extract_blocks(doc):
    """
    从 PDF 中提取所有文本块，返回列表，每个元素为:
        {
            "text": str,
            "page": int (0-based),
            "y0": float, "y1": float,
            "font_size": float,
            "is_bold": bool,
        }
    """
    blocks = []
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        header_y = page_y(page, HEADER_RATIO)
        footer_y = page_y(page, 1.0 - FOOTER_RATIO)

        # 使用 dict 模式获取带格式信息的文本
        text_dict = page.get_text("dict", sort=True)
        for block in text_dict.get("blocks", []):
            if block["type"] != 0:  # 非文本块（图片等）
                continue
            for line in block.get("lines", []):
                bbox = line["bbox"]  # (x0, y0, x1, y1)
                y0, y1 = bbox[1], bbox[3]

                # 拼接该行所有 span 的文本
                spans = line.get("spans", [])
                if not spans:
                    continue
                text = "".join(s["text"] for s in spans)
                font_size = max(s["size"] for s in spans)
                # 判断是否加粗/加重：多数 span 的 font 包含 Bold/Medium/Heavy 等
                bold_keywords = ("bold", "black", "medi", "demi", "heavy", "semi")
                bold_count = sum(
                    1 for s in spans
                    if any(kw in s["font"].lower() for kw in bold_keywords)
                )
                is_bold = bold_count >= len(spans) / 2

                blocks.append({
                    "text": text.strip(),
                    "page": page_idx,
                    "y0": y0,
                    "y1": y1,
                    "font_size": font_size,
                    "is_bold": is_bold,
                    # 标记是否在页眉/页脚区域
                    "in_header": y1 < header_y,
                    "in_footer": y0 > footer_y,
                })
    return blocks


def classify_blocks(blocks):
    """
    将文本块分类为:
      - "header-footer": 页眉/页脚
      - "section-title": 章节标题
      - "body": 正文
      - "reference-start": 参考文献分界线
    """
    # ── 第一遍：统计页眉/页脚候选 ──
    # 收集所有在页眉/页脚区域内的文本行
    header_texts = Counter()
    footer_texts = Counter()
    for b in blocks:
        if b["in_header"] and not is_noise(b["text"]):
            header_texts[normalise(b["text"])] += 1
        if b["in_footer"] and not is_noise(b["text"]):
            footer_texts[normalise(b["text"])] += 1

    # 重复出现 ≥ 总页数一半的视为固定页眉/页脚
    total_pages = max(b["page"] for b in blocks) + 1 if blocks else 0
    repeat_threshold = max(2, total_pages // 2)

    def is_fixed_header_footer(text_norm):
        return (
            header_texts.get(text_norm, 0) >= repeat_threshold
            or footer_texts.get(text_norm, 0) >= repeat_threshold
        )

    # ── 第二遍：分类每个块 ──
    classified = []
    for b in blocks:
        text = b["text"]
        text_norm = normalise(text)

        # 1) 固定页眉/页脚
        if b["in_header"] or b["in_footer"]:
            if is_noise(text) or is_fixed_header_footer(text_norm):
                classified.append({**b, "kind": "header-footer"})
                continue

        # 2) 参考文献分界线
        for pat in REF_PATTERNS:
            if re.match(pat, text, re.IGNORECASE):
                classified.append({**b, "kind": "reference-start"})
                break
        else:
            # 3) 章节标题
            is_section_title = False

            # 先检查文本是否命中章节正则（不包括参考文献）
            matched_section = False
            for _, patterns in SECTION_PATTERNS:
                for pat in patterns:
                    if re.match(pat, text, re.IGNORECASE):
                        matched_section = True
                        break
                if matched_section:
                    break

            # 检查是否命中参考文献正则
            matched_ref = False
            for pat in REF_PATTERNS:
                if re.match(pat, text, re.IGNORECASE):
                    matched_ref = True
                    break

            if matched_section or matched_ref:
                # 字体启发：字号较大或加粗
                font_ok = b["font_size"] >= 11 or b["is_bold"]
                # 结构启发：短行、不以句号结尾
                structural_ok = len(text) < 100 and not text.rstrip().endswith(".")
                if font_ok or structural_ok:
                    is_section_title = True

            if is_section_title:
                classified.append({**b, "kind": "section-title"})
            else:
                classified.append({**b, "kind": "body"})

    return classified


def build_sections(classified_blocks, target_names):
    """
    根据 classified_blocks 构建章节映射。
    返回:
        sections: {section_name: [text_lines]}
        references_start: int | None (block index)
    """
    # 找到所有章节标题的位置
    section_positions = []  # (index, matched_section_name)
    references_start = None

    for i, b in enumerate(classified_blocks):
        if b["kind"] == "reference-start" and references_start is None:
            references_start = i
        if b["kind"] != "section-title":
            continue
        text = normalise(b["text"])
        # 检查是否命中目标章节
        for name, patterns in SECTION_PATTERNS:
            for pat in patterns:
                if re.match(pat, b["text"], re.IGNORECASE):
                    section_positions.append((i, name))
                    break
            else:
                continue
            break
        # 检查是否是参考文献（终止边界）
        for pat in REF_PATTERNS:
            if re.match(pat, b["text"], re.IGNORECASE):
                if references_start is None:
                    references_start = i
                break

    # 按目标章节分组文本
    sections = {name: [] for name in target_names}
    name_to_idx = {name: i for i, name in enumerate(target_names)}

    if not section_positions:
        return sections, references_start

    # 对每个命中的章节，确定其文本范围
    for idx, (pos, name) in enumerate(section_positions):
        start = pos + 1  # 章节标题之后的第一行
        # 结束位置：下一个章节标题的位置（或参考文献分界线）
        if idx + 1 < len(section_positions):
            end = section_positions[idx + 1][0]
        else:
            end = references_start if references_start is not None else len(classified_blocks)

        # 收集 start 到 end 之间的 body 文本
        lines = []
        for j in range(start, end):
            b = classified_blocks[j]
            if b["kind"] in ("body", "section-title"):  # 子标题也算
                # 过滤掉明显是图表标题的行
                txt = b["text"]
                if re.match(r"^\s*(figure|fig\.|table|tab\.)\s*\d+", txt, re.IGNORECASE):
                    continue
                lines.append(txt)
        sections[name] = lines

    return sections, references_start


# ── 主入口 ────────────────────────────────────────────────────────────

def extract_paper(pdf_path: str) -> str:
    """从 PDF 提取章节文本，返回拼接后的字符串。"""
    doc = fitz.open(pdf_path)

    # 1) 提取所有文本块
    blocks = extract_blocks(doc)

    # 2) 分类
    classified = classify_blocks(blocks)

    # 3) 构建章节
    target_names = ["abstract", "introduction", "method", "experiments", "conclusion"]
    sections, _ = build_sections(classified, target_names)

    # 4) 组装输出
    section_labels = {
        "abstract": "Abstract",
        "introduction": "Introduction",
        "method": "Method",
        "experiments": "Experiments",
        "conclusion": "Conclusion",
    }

    output_parts = []
    for name in target_names:
        lines = sections.get(name, [])
        if not lines:
            continue
        output_parts.append(f"{'=' * 60}")
        output_parts.append(f"  {section_labels[name]}")
        output_parts.append(f"{'=' * 60}")
        output_parts.append("")
        output_parts.extend(lines)
        output_parts.append("")

    doc.close()
    return "\n".join(output_parts)


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(f"用法: python {Path(__file__).name} input.pdf [output.txt]")
        print(f"      output.txt 可选，默认与 PDF 同名放在同目录下")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if len(sys.argv) >= 3:
        out_path = sys.argv[2]
    else:
        # 自动生成输出路径：把 .pdf 替换为 .txt
        p = Path(pdf_path)
        out_path = str(p.with_suffix(".txt"))

    if not Path(pdf_path).exists():
        print(f"[错误] 找不到文件: {pdf_path}")
        sys.exit(1)

    print(f"正在读取: {pdf_path}")
    result = extract_paper(pdf_path)

    Path(out_path).write_text(result, encoding="utf-8")
    print(f"已输出: {out_path}")
    print(f"共 {len(result)} 字符")


if __name__ == "__main__":
    main()
