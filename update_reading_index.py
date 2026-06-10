#!"F:/Anaconda3/space/envs/paper_reader/python.exe"
"""
update_reading_index.py — 扫描 Reading_List/ 和 Papers/，自动生成阅读索引。

用法:
    python update_reading_index.py
"""

import re
from pathlib import Path
from datetime import date

VAULT_ROOT = Path(__file__).parent
READING_LIST_DIR = VAULT_ROOT / "Reading_List"
PAPERS_DIR = VAULT_ROOT / "Papers"


def parse_frontmatter(filepath: Path) -> dict:
    """从 Markdown 文件中提取 YAML frontmatter 字段。支持嵌套列表。"""
    if not filepath.exists():
        return {}
    text = filepath.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    current_key = None
    for line in m.group(1).split("\n"):
        kv = re.match(r"^\s*(\w+):\s*(.*)", line)
        if kv and not line.strip().startswith("-"):
            key = kv.group(1)
            val = kv.group(2).strip().strip('"').strip("'")
            fm[key] = val if val else ""
            current_key = key
        elif line.strip().startswith("-"):
            tag_val = line.strip().lstrip("-").strip().strip('"').strip("'")
            if current_key and current_key in fm:
                existing = fm[current_key]
                if isinstance(existing, list):
                    existing.append(tag_val)
                else:
                    fm[current_key] = [tag_val] if not existing else [existing, tag_val]
            elif current_key:
                fm[current_key] = [tag_val]
    return fm


def build_index():
    """扫描 Reading_List/，生成索引。"""
    deep_reads = sorted(READING_LIST_DIR.glob("*.md"))
    # 排除索引文件自身
    deep_reads = [f for f in deep_reads if f.name != "README.md"]

    lines = [
        "# 📚 论文阅读索引",
        "",
        f"> 自动生成于 {date.today().isoformat()}  |  共 {len(deep_reads)} 篇已读论文",
        "",
        "| # | 论文 | 会议/期刊 | 年份 | 方向 | 翻译笔记 |",
        "|---|------|----------|------|------|----------|",
    ]

    for i, dr_path in enumerate(deep_reads, 1):
        fm = parse_frontmatter(dr_path)
        title = fm.get("title", dr_path.stem.replace(" 深度解读", ""))
        venue = fm.get("venue", "-")
        year = fm.get("year", "-")

        # 提取方向标签
        tags_field = fm.get("tags", [])
        if isinstance(tags_field, list):
            dir_tag = next((t.lstrip("#") for t in tags_field if "深度解读" not in t), "-")
        else:
            dir_tag = fm.get("direction", "-")

        # 查找对应的 Papers/ 笔记
        paper_note = fm.get("paper_note", "")
        paper_link = re.search(r"\[\[(.+?)\]\]", paper_note)
        if paper_link:
            paper_name = paper_link.group(1)
            paper_path = PAPERS_DIR / f"{paper_name}.md"
            if paper_path.exists():
                lines.append(
                    f"| {i} | [[{dr_path.stem}\\|{title}]] | {venue} | {year} "
                    f"| #{dir_tag} | [[{paper_name}]] |"
                )
            else:
                lines.append(
                    f"| {i} | [[{dr_path.stem}\\|{title}]] | {venue} | {year} "
                    f"| #{dir_tag} | — |"
                )
        else:
            lines.append(
                f"| {i} | [[{dr_path.stem}\\|{title}]] | {venue} | {year} "
                f"| #{dir_tag} | — |"
            )

    lines.append("")
    lines.append("> 点击论文名跳转到深度解读，点击翻译笔记列跳转到对应翻译。")

    index_path = READING_LIST_DIR / "README.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"索引已更新: {index_path}")
    print(f"共 {len(deep_reads)} 篇论文")


if __name__ == "__main__":
    build_index()
