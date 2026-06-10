# Paper Reader — Claude Code 论文阅读技能

![](asset/图片.jpg)

一个论文阅读技能，实现五阶段论文阅读工作流：PDF 提取 → 章节翻译 → 翻译笔记 → 深度解读 → 自动索引。

## 设计理念

面向硕博新生，核心理念是**翻译自己读，解读对答案**：

- `Papers/` 里只有翻译 + 一句话总结 + 创新点——不剧透，你形成独立判断
- `Reading_List/` 里有完整深度解读——读完翻译后对照验证自己的理解
- `Reading_List/README.md` 自动维护阅读索引，随时知道读了多少、读了什么
- 两个目录物理隔离，通过 Obsidian 双向链接互联

## 环境要求

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [Obsidian](https://obsidian.md/)（可选，用于笔记管理与图谱可视化）
- Python 3.10+，推荐 conda 环境

```bash
conda create -n paper_reader python=3.10 -y
conda activate paper_reader
pip install pymupdf
```

## 安装

```bash
# 1. 克隆仓库
git clone https://github.com/<your-username>/paper_reader.git

# 2. 安装技能到 Claude Code
# Windows:
mkdir F:\Claude\skills\paper_reader
cp SKILL.md F:\Claude\skills\paper_reader\
cmd /c "mklink /J %USERPROFILE%\.claude\skills\paper_reader F:\Claude\skills\paper_reader"

# macOS / Linux:
mkdir -p ~/.claude/skills/paper_reader
cp SKILL.md ~/.claude/skills/paper_reader/
```

## 在 Obsidian 中设置

1. 复制模板到你的 Obsidian Vault：

```bash
cp templates/paper_template.md "<你的vault>/Templates/"
cp templates/paper_deep_read_template.md "<你的vault>/Templates/"
```

2. 将 `extract_paper.py` 和 `update_reading_index.py` 放入 Vault 根目录，或修改 `SKILL.md` 中的脚本路径指向它们。

3. 在 Vault 根目录创建 `raw_pdfs/`、`Papers/`、`Reading_List/` 三个文件夹。

## Obsidian Vault 目录结构

完成安装后，你的 Obsidian Vault 应该长这样：

```
我的论文阅读/                       ← Vault 根目录
├── Templates/                     ← 模板文件夹
│   ├── paper_template.md          # Papers/ 笔记模板
│   └── paper_deep_read_template.md # Reading_List/ 深度解读模板
├── raw_pdfs/                      ← 原始 PDF（推荐按日期子文件夹管理）
│   └── 2024_01_15/
│       ├── SomePaper.pdf
│       └── AnotherPaper.pdf
├── Papers/                        ← 翻译笔记（你自己读的）
│   ├── CVPR20 · Face X-ray · 翻译+轻分析.md
│   └── ECCV20 · F3-Net · 翻译+轻分析.md
├── Reading_List/                  ← 深度解读（读完对答案）
│   ├── README.md                  # 自动生成的阅读索引
│   ├── CVPR20 · Face X-ray · 深度解读.md
│   └── ECCV20 · F3-Net · 深度解读.md
├── extract_paper.py               # PDF 提取 + 元数据脚本
├── update_reading_index.py        # 阅读索引更新脚本
└── .obsidian/                     # Obsidian 自动生成
    └── graph.json                 # 图谱配置
```

图谱效果：Papers/ 节点（蓝色）和 Reading_List/ 节点（橙色）通过 `deep_read` ↔ `paper_note` 双向链接互联，一目了然。

## 使用

```bash
# 单篇论文
/paper_reader raw_pdfs/my_paper.pdf

# 批量处理整个文件夹
/paper_reader raw_pdfs/2024_neurips/

# 不带参数 → 列出可用 PDF
/paper_reader
```

## 辅助命令

```bash
# 提取 PDF 元数据（DOI、标题、作者、年份）
python extract_paper.py --meta paper.pdf

# 手动更新阅读索引
python update_reading_index.py
```

## 工作流（五阶段）

```
PDF → 提取 TXT → 翻译 → Papers/（翻译 + 一句话总结 + 创新点）
                         ↘
                           Reading_List/（详细深度解读，参考答案）
                                    ↘
                                      Reading_List/README.md（自动索引）
```

| 阶段 | 功能 | 输出 |
|------|------|------|
| 1 | PyMuPDF 提取章节文本（含非标准论文兜底） | `.txt` 文件 |
| 2 | 逐段翻译成中文 | 内存 |
| 3 | 生成 Papers/ 笔记 | 翻译原文 + 🎯总结 + ✨创新点 |
| 4 | 生成 Reading_List/ 深度解读 | 📌定位 + 🔑方法 + 👍亮点 + 👎局限 + 💡思考 + 🔗关联 + ❓建议 |
| 5 | 更新 Reading_List/README.md | 自动维护的阅读索引表 |

## 文件说明

| 文件 | 用途 |
|------|------|
| `SKILL.md` | 技能定义，Claude Code 加载的核心 |
| `extract_paper.py` | PDF 章节提取（含非标准论文兜底）+ 元数据提取（`--meta`） |
| `update_reading_index.py` | 扫描 Reading_List/ 自动生成阅读索引 |
| `templates/paper_template.md` | Papers/ 笔记模板（翻译 + 轻分析） |
| `templates/paper_deep_read_template.md` | Reading_List/ 深度解读模板 |

## 领域通用性

不绑定任何特定研究领域。`direction` 和标签从论文内容自动推断，深度解读自动适配论文所属领域。已通过 CV、计算生物学等跨领域论文验证。

## 自定义

直接编辑 `SKILL.md` 修改工作流。添加翻译原则、章节划分、分析维度均可在此文件中调整。改动立即生效，无需重启。
