---
name: paper_reader
description: "论文阅读工作流：PDF 提取 → 章节翻译 → Papers/ 笔记（翻译+轻分析）→ Reading_List/ 深度解读（参考答案）。触发条件：用户提到\"读论文\"、\"论文阅读\"、\"paper reader\"、\"/paper_reader\"，或需要从 PDF 生成论文笔记时。"
---

# Paper Reader — 论文阅读工作流

## 环境配置

- Python: `F:/Anaconda3/space/envs/paper_reader/python.exe`
- 提取脚本: `e:/obsidianSpace/论文阅读/extract_paper.py`
- 笔记模板: `e:/obsidianSpace/论文阅读/Templates/paper_template.md`
- 深度解读模板: `e:/obsidianSpace/论文阅读/Templates/paper_deep_read_template.md`
- 论文笔记输出: `e:/obsidianSpace/论文阅读/Papers/`
- 深度解读输出: `e:/obsidianSpace/论文阅读/Reading_List/`
- 原始 PDF: `e:/obsidianSpace/论文阅读/raw_pdfs/`

## 触发规则

**如果用户调用此技能时没有提供 PDF 路径参数**（即 ARGUMENTS 为空），则：

1. 不要直接运行工作流
2. 先扫描 `raw_pdfs/` 目录下列出可用的 PDF 文件
3. 展示未处理的 PDF 列表，请用户选择
4. 等待用户指定具体 PDF 或确认批量处理

**如果 ARGUMENTS 非空**，直接进入四阶段工作流。

## 工作流（四阶段）

```
PDF → 提取 TXT → 翻译 → Papers/（翻译 + 一句话总结 + 创新点）
                         ↘
                           Reading_List/（详细深度解读，参考答案）
```

新手使用方式：先读 Papers/ 里的翻译，形成自己的理解 → 再去 Reading_List/ 翻参考答案对照。两者通过 Obsidian 双向链接连接。

### 阶段 1：提取章节文本

对每个输入的 PDF，运行：

```bash
cd "e:/obsidianSpace/论文阅读"
"F:/Anaconda3/space/envs/paper_reader/python.exe" extract_paper.py "<pdf_path>"
```

会在 PDF 同目录下生成同名的 `.txt` 文件。

如果用户说"批量处理"或给了文件夹路径，则遍历文件夹下的所有 `.pdf`：

```bash
for f in "<pdf_dir>"/*.pdf; do
    "F:/Anaconda3/space/envs/paper_reader/python.exe" extract_paper.py "$f"
done
```

### 阶段 2：章节翻译

读取阶段 1 产生的 `.txt` 文件，将每个章节**逐段忠实翻译成中文**。

翻译原则：
- **准确第一**：技术术语保持原文含义，不自由发挥
- **可读第二**：拆分英文长句为中文短句，但信息不增不减
- **表格跳过**：表格数据不逐行翻译，标注 `[表格：xxx]` 即可
- **公式跳过**：公式不翻译，标注 `[公式]`
- **图片标注跳过**：Figure/Table 的标题和引用不翻

五个章节翻译要点：
1. **Abstract** — 逐段翻译，保留所有关键信息
2. **Introduction** — 重点翻译问题动机和贡献段落，相关工作部分可适当精简
3. **Method** — 逐段翻译，公式处标注 `[公式]`，但公式前后的文字解释必须完整翻译
4. **Experiments** — 翻译实验设置和结论性句子，表格数据只留关键数字
5. **Conclusion** — 全文翻译，特别是局限性和未来工作部分

### 阶段 3：生成 Obsidian 笔记

将翻译结果和轻分析填入模板 `e:/obsidianSpace/论文阅读/Templates/paper_template.md`，生成笔记到 `e:/obsidianSpace/论文阅读/Papers/`。

**笔记结构**（翻译在前，分析在后）：

```
## 📖 Abstract          ← 阶段2翻译
## 📖 Introduction      ← 阶段2翻译
## 📖 Method            ← 阶段2翻译
## 📖 Experiments       ← 阶段2翻译
## 📖 Conclusion        ← 阶段2翻译
---                    ← 分隔线
## 🎯 一句话总结         ← AI轻分析
## ✨ 创新点            ← AI轻分析（列表）
```

**Frontmatter 填充规则：**
- `direction`: 从论文摘要和关键词**自动推断**研究方向标签（如 DeepFakeDetection、LLM、强化学习、图神经网络 等），不预设固定值
- `title`: 论文完整标题
- `venue`: 会议/期刊名
- `year`: 发表年份
- `tags`: 第一个固定 `#待精读`，第二个**根据 direction 自动填入**，可继续追加
- `link`: arXiv 链接或 DOI
- `deep_read`: `[[论文标题 深度解读]]` — 指向阶段4生成的 Reading_List 笔记
- `related`: 留空 `[]`
- `status`: 设为 `已读摘要`
- `date`: 当天日期，格式 `YYYY-MM-DD`

**轻分析规则（只写两项）：**
- `🎯 一句话总结` — 用大白话说清论文做了什么，不超过 5 句话
- `✨ 创新点` — 列表形式，每点一句话

### 阶段 4：生成深度解读

将阶段 2 的翻译和阶段 3 的轻分析作为基础，以**该领域资深导师**的角色写一份详细解读，存入 `e:/obsidianSpace/论文阅读/Reading_List/`。角色立场：熟悉该论文所属领域的现状、发展脉络和代表性工作，但不局限于特定子领域。

**文件名**：`论文标题 深度解读.md`（PDF 文件名去掉 `.pdf` + ` 深度解读` 后缀）

**使用模板**：`e:/obsidianSpace/论文阅读/Templates/paper_deep_read_template.md`

**解读章节（共 10 节）：**

1. **📌 论文定位** — 这篇在领域中处于什么位置？前面有什么代表性工作，后面有哪些跟进？让研0知道这篇的"坐标"
2. **🎯 一句话总结** — 同阶段3，保持一致
3. **🔑 核心方法** — 关键思路 + 公式通俗解释 + 方法流程。公式用大白话解释其物理含义，不只列公式
4. **✨ 创新点** — 列表，每点一句话
5. **👍 亮点** — 论文最巧妙的设计（2-3 点），解释为什么妙
6. **👎 局限 & 改进方向** — 局限和可能的改进思路
7. **📊 实验结果要点** — 提炼关键发现，不列全表
8. **💡 我的思考** — 导师视角的点评，结合领域现状和发展趋势
9. **🔗 与其他论文的关联** — 扫描 Papers/ 中已有的笔记，如发现相关论文（同领域、同方法线、技术继承关系等），在此建立链接并简述关联。如已有笔记中无相关论文，则留空
10. **❓ 阅读建议** — 建议的阅读顺序、容易卡住的地方、值得深挖的问题

**双向链接**：阶段 3 的 Papers/ 笔记的 `deep_read` 字段指向这里，这里的 `paper_note` 字段指向 Papers/ 笔记。Obsidian 图谱中形成双向边。

## 设计原则

本工作流面向研0学生，核心理念是**翻译自己读，解读对答案**：
- Papers/ 里只有翻译 + 一句话总结 + 创新点——不剧透，让你形成独立判断
- Reading_List/ 里有完整深度解读——读完翻译后对照验证自己的理解
- 两个目录物理隔离，双向链接连接。不看 Reading_List 就不会被剧透

## 使用方式

- `/paper_reader <pdf路径>` — 单篇论文
- `/paper_reader <文件夹路径>` — 批量处理
- "读一下这篇论文 <路径>" — 自然语言触发

## 优化记录

- 2026-06-03: 初始版本，三阶段工作流（提取 → 分析 → 入库）
- 2026-06-03: v2 重构——将"全量分析"改为"翻译 + 轻分析"，面向研0学生优化
- 2026-06-04: v3 新增阶段4——深度解读存入 Reading_List/，与 Papers/ 物理隔离、双向链接。实现"翻译自己读，解读对答案"的设计理念。同时优化解读模板，新增 📌论文定位 和 🔗与其他论文的关联 两个章节
- 2026-06-04: 通用化——移除 CV 领域绑定，direction/tag 从论文内容自动推断，🔗关联改为扫描已有笔记动态建立，导师角色改为"该领域资深导师"
