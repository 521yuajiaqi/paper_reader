#!"F:/Anaconda3/space/envs/paper_reader/python.exe"
"""
extract_paper.py — 从学术论文 PDF 中提取关键章节文字和元数据。

用法:
    python extract_paper.py input.pdf [output.txt] [--meta]

    不加 --meta: 输出提取的章节文本
    加 --meta:   输出 JSON 格式的元数据 {title, doi, authors, year}

依赖:
    pip install pymupdf
"""

import sys
import re
import json
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF


# ── 配置 ──────────────────────────────────────────────────────────────

HEADER_RATIO = 0.12
FOOTER_RATIO = 0.10

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

REF_PATTERNS = [
    r"^\s*references?\s*$",
    r"^\s*bibliography\s*$",
    r"^\s*R\s*E\s*F\s*E\s*R\s*E\s*N\s*C\s*E\s*S\s*$",
]

NOISE_PATTERNS = [
    r"^\s*\d+\s*$",
    r"^\s*\d+\s*/\s*\d+\s*$",
    r"^©\s*\d{4}",
    r"^\s*arXiv:\d{4}\.\d{4,}(v\d+)?\s*$",
    r"^\s*Preprint",
    r"^\s*submitted\s+to\s+",
]


# ── 工具函数 ──────────────────────────────────────────────────────────

def page_y(page, ratio):
    _, _, _, height = page.rect
    return height * ratio


def is_noise(text):
    for pat in NOISE_PATTERNS:
        if re.match(pat, text, re.IGNORECASE):
            return True
    return False


def normalise(s):
    return " ".join(s.split()).lower()


# ── 元数据提取 ────────────────────────────────────────────────────────

def extract_metadata(pdf_path: str) -> dict:
    """从 PDF 提取元数据：标题、DOI、作者、年份、arXiv ID。"""
    doc = fitz.open(pdf_path)
    meta = {"title": "", "doi": "", "authors": "", "year": "", "arxiv": ""}

    # 1) PDF 内嵌元数据
    pdf_meta = doc.metadata
    if pdf_meta.get("title"):
        meta["title"] = pdf_meta["title"].strip()
    if pdf_meta.get("author"):
        meta["authors"] = pdf_meta["author"].strip()

    # 2) 从前 3 页文本中搜索 DOI 和 arXiv ID
    full_text = ""
    for p in range(min(3, len(doc))):
        full_text += doc[p].get_text("text", sort=True) + "\n"

    # DOI: 10.xxxx/xxxxx...
    doi_match = re.search(r'\b(10\.\d{4,}/[^\s]+)\b', full_text)
    if doi_match:
        meta["doi"] = doi_match.group(1).rstrip(".")

    # arXiv: xxxx.xxxxx
    arxiv_match = re.search(r'arxiv:(\d{4}\.\d{4,}(?:v\d+)?)', full_text, re.IGNORECASE)
    if arxiv_match:
        meta["arxiv"] = arxiv_match.group(1)

    # 年份：从 DOI 或 arXiv 或文本中提取
    year_match = re.search(r'(?:19|20)(\d{2})', meta.get("arxiv", ""))
    if year_match:
        meta["year"] = f"20{year_match.group(1)}"
    else:
        year_match = re.search(r'(?:Published|Accepted|Received).*?(20\d{2})', full_text)
        if year_match:
            meta["year"] = year_match.group(1)

    doc.close()
    return meta


# ── 核心逻辑 ──────────────────────────────────────────────────────────

def extract_blocks(doc):
    blocks = []
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        header_y = page_y(page, HEADER_RATIO)
        footer_y = page_y(page, 1.0 - FOOTER_RATIO)

        text_dict = page.get_text("dict", sort=True)
        for block in text_dict.get("blocks", []):
            if block["type"] != 0:
                continue
            for line in block.get("lines", []):
                bbox = line["bbox"]
                y0, y1 = bbox[1], bbox[3]

                spans = line.get("spans", [])
                if not spans:
                    continue
                text = "".join(s["text"] for s in spans)
                font_size = max(s["size"] for s in spans)
                bold_keywords = ("bold", "black", "medi", "demi", "heavy", "semi")
                bold_count = sum(
                    1 for s in spans
                    if any(kw in s["font"].lower() for kw in bold_keywords)
                )
                is_bold = bold_count >= len(spans) / 2

                blocks.append({
                    "text": text.strip(),
                    "page": page_idx,
                    "y0": y0, "y1": y1,
                    "font_size": font_size,
                    "is_bold": is_bold,
                    "in_header": y1 < header_y,
                    "in_footer": y0 > footer_y,
                })
    return blocks


def classify_blocks(blocks):
    header_texts = Counter()
    footer_texts = Counter()
    for b in blocks:
        if b["in_header"] and not is_noise(b["text"]):
            header_texts[normalise(b["text"])] += 1
        if b["in_footer"] and not is_noise(b["text"]):
            footer_texts[normalise(b["text"])] += 1

    total_pages = max(b["page"] for b in blocks) + 1 if blocks else 0
    repeat_threshold = max(2, total_pages // 2)

    def is_fixed_header_footer(text_norm):
        return (
            header_texts.get(text_norm, 0) >= repeat_threshold
            or footer_texts.get(text_norm, 0) >= repeat_threshold
        )

    classified = []
    for b in blocks:
        text = b["text"]
        text_norm = normalise(text)

        if b["in_header"] or b["in_footer"]:
            if is_noise(text) or is_fixed_header_footer(text_norm):
                classified.append({**b, "kind": "header-footer"})
                continue

        for pat in REF_PATTERNS:
            if re.match(pat, text, re.IGNORECASE):
                classified.append({**b, "kind": "reference-start"})
                break
        else:
            is_section_title = False
            matched_section = False
            for _, patterns in SECTION_PATTERNS:
                for pat in patterns:
                    if re.match(pat, text, re.IGNORECASE):
                        matched_section = True
                        break
                if matched_section:
                    break

            matched_ref = False
            for pat in REF_PATTERNS:
                if re.match(pat, text, re.IGNORECASE):
                    matched_ref = True
                    break

            if matched_section or matched_ref:
                font_ok = b["font_size"] >= 11 or b["is_bold"]
                structural_ok = len(text) < 100 and not text.rstrip().endswith(".")
                if font_ok or structural_ok:
                    is_section_title = True

            if is_section_title:
                classified.append({**b, "kind": "section-title"})
            else:
                classified.append({**b, "kind": "body"})

    return classified


def build_sections(classified_blocks, target_names):
    section_positions = []
    references_start = None

    for i, b in enumerate(classified_blocks):
        if b["kind"] == "reference-start" and references_start is None:
            references_start = i
        if b["kind"] != "section-title":
            continue
        for name, patterns in SECTION_PATTERNS:
            for pat in patterns:
                if re.match(pat, b["text"], re.IGNORECASE):
                    section_positions.append((i, name))
                    break
            else:
                continue
            break
        for pat in REF_PATTERNS:
            if re.match(pat, b["text"], re.IGNORECASE):
                if references_start is None:
                    references_start = i
                break

    sections = {name: [] for name in target_names}

    if not section_positions:
        return sections, references_start

    for idx, (pos, name) in enumerate(section_positions):
        start = pos + 1
        if idx + 1 < len(section_positions):
            end = section_positions[idx + 1][0]
        else:
            end = references_start if references_start is not None else len(classified_blocks)

        lines = []
        for j in range(start, end):
            b = classified_blocks[j]
            if b["kind"] in ("body", "section-title"):
                txt = b["text"]
                if re.match(r"^\s*(figure|fig\.|table|tab\.)\s*\d+", txt, re.IGNORECASE):
                    continue
                lines.append(txt)
        sections[name] = lines

    return sections, references_start


def extract_full_text(doc) -> str:
    """兜底模式：按页提取全部文本，适用于 Nature/Science 等非标准格式论文。"""
    lines = []
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        text = page.get_text("text", sort=True)
        # 过滤纯空行和明显噪声
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped or is_noise(stripped):
                continue
            if re.match(r"^\s*(figure|fig\.|table|tab\.)\s*\d+", stripped, re.IGNORECASE):
                continue
            lines.append(stripped)
    return "\n".join(lines)


# ── 主入口 ────────────────────────────────────────────────────────────

def extract_paper(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)

    blocks = extract_blocks(doc)
    classified = classify_blocks(blocks)

    target_names = ["abstract", "introduction", "method", "experiments", "conclusion"]
    sections, _ = build_sections(classified, target_names)

    section_labels = {
        "abstract": "Abstract",
        "introduction": "Introduction",
        "method": "Method",
        "experiments": "Experiments",
        "conclusion": "Conclusion",
    }

    # 检查是否所有章节都为空 → 兜底模式
    total_lines = sum(len(sections[name]) for name in target_names)
    if total_lines == 0:
        full_text = extract_full_text(doc)
        doc.close()
        output = []
        output.append(f"{'=' * 60}")
        output.append("  全文 (非标准格式论文，未做章节切分)")
        output.append(f"{'=' * 60}")
        output.append("")
        output.append(full_text)
        return "\n".join(output)

    # 正常章节输出
    output_parts = []
    for name in target_names:
        lines_data = sections.get(name, [])
        if not lines_data:
            continue
        output_parts.append(f"{'=' * 60}")
        output_parts.append(f"  {section_labels[name]}")
        output_parts.append(f"{'=' * 60}")
        output_parts.append("")
        output_parts.extend(lines_data)
        output_parts.append("")

    doc.close()
    return "\n".join(output_parts)


def main():
    if len(sys.argv) < 2:
        print(f"用法: python {Path(__file__).name} input.pdf [output.txt] [--meta]")
        print(f"      --meta  输出 JSON 元数据而非提取文本")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"[错误] 找不到文件: {pdf_path}")
        sys.exit(1)

    # 元数据模式
    if "--meta" in sys.argv:
        meta = extract_metadata(pdf_path)
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return

    # 提取模式
    if len(sys.argv) >= 3 and not sys.argv[2].startswith("--"):
        out_path = sys.argv[2]
    else:
        p = Path(pdf_path)
        out_path = str(p.with_suffix(".txt"))

    print(f"正在读取: {pdf_path}")
    result = extract_paper(pdf_path)

    Path(out_path).write_text(result, encoding="utf-8")
    print(f"已输出: {out_path}")
    print(f"共 {len(result)} 字符")


if __name__ == "__main__":
    main()
