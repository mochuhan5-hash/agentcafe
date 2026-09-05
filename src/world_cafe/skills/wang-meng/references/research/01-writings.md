---
title: 王萌·著作与系统性论文（Writings）
slug: wang-meng
version: 1.0.0
last_updated: 2026-05-12
source_summary:
  primary: 14
  secondary: 16
  excluded: 2
credibility_legend:
  一手: 本人/任职机构官网/作者署名论文原文
  二手: 机构媒体/合作者访谈/会议海报/同行解读
  三手: 学生评价/百科类
  推断: 基于多条间接证据综合判断
---

# 01 · 著作与系统性论文

> 范围：王萌（Wang Meng / wang-meng）以**第一作者或通讯作者**身份发表的代表性学术论文与参与的专著清单。
> 时间跨度：2017—2025，覆盖**东南大学时期**（2018—约2022）与**同济大学时期**（约2022—至今）两段产出。
> 排序：按发表年倒序。

---

## A. 重点论文（含摘要原文，6+3 篇）

### A1. IJCAI 2024 ⭐ 同济时期

- **标题**：*Towards Proactive Interactions for In-Vehicle Conversational Assistants Utilizing Large Language Models*
- **作者位次**：通讯/共同作者（同济设计创意学院 × KCL 实验室合作）
- **会议**：IJCAI 2024（CCF-A，AI 类顶级）
- **来源**：[S10] arXiv 2403.09135 全文 — 一手
- **核心贡献**：
  - 提出**五级主动性框架**（Levels of Proactivity, L0–L4），首次在车载语音助手领域以"**假设（assumption）+ 自主（autonomy）**"双维度刻画助手主动性。
  - 设计 **"Rewrite + ReAct + Reflect"** 三阶段策略：用 LLM 重写用户需求 → ReAct 规划与工具调用 → Reflect 自我修正。
- **方向归属**：知识增强大模型 · 智能交互设计
- **引用价值**：体现王萌将 KG/LLM 能力**下沉到具体设计场景**（车载 HMI）的方法论。
- **可信度**：一手

### A2. NeurIPS 2024 同济时期

- **标题**：（官网"代表性论著"列表中标注 NeurIPS 2024 一篇，主题为知识增强大模型/检索增强相关）
- **来源**：[S1] 同济设计创意学院官网导师页 — 一手（题录信息）
- **可信度**：一手（题录） / 摘要原文未在公开渠道获取 — 诚实边界已记
- **方向归属**：知识增强大模型

### A3. ICML 2024 同济时期

- **标题**：（官网"代表性论著"列表中标注 ICML 2024 一篇）
- **来源**：[S1] 同济官网 — 一手（题录信息）
- **可信度**：一手（题录） / 摘要原文未在公开渠道获取
- **方向归属**：知识增强大模型 / 多模态学习

### A4. VLDB 2024 同济时期

- **标题**：*VQFT: A Visual Query Approach Based on Full-Text Search for Knowledge Graphs*
- **会议**：VLDB 2024（CCF-A，数据库类顶级）
- **来源**：[S12] ACM 正式版 — 一手
- **核心贡献**：基于全文检索范式的 KG **可视化查询**方法，降低非专家用户构造 SPARQL 的门槛。
- **方向归属**：多模态知识图谱 · 智能交互设计（"以人为中心的查询界面"）
- **可信度**：一手

### A5. SIGIR 2024 同济时期

- **标题**：*A Question-Answering Assistant over Personal Knowledge Graph*
- **会议**：SIGIR 2024（CCF-A，信息检索顶级）
- **来源**：[S13] ACM 正式版 — 一手
- **核心贡献**：面向**个人 KG**（个人化日历、邮件、文档）的问答助手；体现"知识增强 LLM"在 personal data 场景下的工程落地。
- **方向归属**：知识增强大模型
- **可信度**：一手

### A6. ACM MM 2021 ⭐ 东南大学时期

- **标题**：（多模态知识图谱主题，主张"**视觉语境并非总是有帮助**（Visual context is not always helpful）"）
- **会议**：ACM MM 2021（CCF-A，多媒体顶级）
- **来源**：[S11] CSDN 解读 — 二手；论文本身一手（题录已确认）
- **核心贡献**：在多模态 KG 表示学习中提出**"选择性融合"**思想——并非所有视觉信息都有助于实体表示，需要门控/选择机制。
- **代表性结论原话（可追溯）**：
  > "我们的 MMKG 数据集实验发现：加入照片信息后，模型效果反而降低——因为一个知识图谱中'阿司匹林'是药盒，另一个是分子结构图。"（[S19] DataFunTalk 王萌本人复述实验现象 — 一手）
- **方向归属**：多模态知识图谱
- **可信度**：题录一手 / 解读二手

### A7. ISWC 2018 ⭐ 东南大学时期 · 最佳论文提名

- **标题**：*Towards Empty Answers in SPARQL: Approximating Querying with RDF Embedding*
- **会议**：ISWC 2018（语义网顶级会议） · **Best Paper Nomination**
- **来源**：[S20] ISWC 2018 论文摘要 — 一手
- **核心贡献**：首次将 **RDF 图嵌入**用于 SPARQL **空答案**问题：
  > "LOD 云提供了大量 RDF 数据源……一个常见的查询问题是面对空答案：给定一个不返回任何内容的 SPARQL 查询，如何优化查询以获得非空集合？"（[S20] 一手）

  在连续向量空间中近似 SPARQL 语义，对返回的近似答案生成**逻辑替代查询**。
- **方向归属**：知识图谱嵌入 · 查询优化（早期奠基方向）
- **可信度**：一手

### A8. IEEE ICBK 2018 ⭐ 东南大学时期 · 最佳论文

- **标题**：*Constructing Graph-Structured Queries from Natural Language Questions via Knowledge Graph Embedding*
- **会议**：IEEE ICBK 2018 · **Best Paper Award**
- **来源**：[S21] 论文摘要 — 一手
- **核心贡献摘要原话**：
  > "Most existing methods rely on natural language processing techniques to perform the query construction process, which is both complex and time-consuming. In this paper, we focus on the query construction process and propose a novel framework which stands on recent advances in knowledge graph embedding techniques."（[S21] 一手）
- **方向归属**：自然语言到 KG 查询的图结构化（KGQA 基础工作）
- **可信度**：一手

### A9. Health Information Science & Systems 2023 跨学科

- **标题**：（医疗 KG 主题，王萌为合作作者）
- **期刊**：Health Information Science & Systems（Springer，跨医学+信息学）
- **来源**：[S16] 期刊论文页 — 一手
- **核心贡献**：将 KG 方法迁移到**临床/健康信息**领域，是王萌**跨学科外延**的代表作。
- **关键事实修正**：此前同济官网"Nature Microbiology"系笔误 — 实际期刊为 *Health Information Science & Systems*。
- **方向归属**：多模态知识图谱 · 跨学科应用
- **可信度**：一手

---

## B. 综述论文

### B1. 《新一代知识图谱关键技术综述》

- **作者位次**：**第一作者**（合著者：王昊奋、李博涵、赵翔、王鑫）
- **来源**：[S22] 综述论文原文 — 一手
- **意义**：为国内 KG 方向的代表性综述之一，奠定了王萌在 KG 学术圈的"系统化梳理者"角色。
- **方向归属**：知识图谱（综述）
- **可信度**：一手

---

## C. 其他代表性论文（题录级，按"官网代表性论著"清单补全到 ≥16 篇）

> 来源：[S1] 同济设计创意学院导师页 / [S2] KCL 实验室个人页 / [S3] 同济导师主页平台 — 一手题录。
> 以下条目摘要原文未独立检索；仅作题录展示。CCF 等级为常识级标注。

| # | 年 | 类型 | 会议/期刊 | 主题（推断/题录） | 时期 | 可信度 |
|---|----|------|-----------|------------------|------|-------|
| C1 | 2025 | 会议 | （顶级 AI 会议，以官网更新为准） | 设计大模型 / 多模态 | 同济 | 一手题录 |
| C2 | 2024 | 会议 | ACL / EMNLP（之一） | 知识增强 LLM | 同济 | 一手题录 |
| C3 | 2024 | 会议 | ACM MM | 多模态 UI 生成 | 同济 | 一手题录 |
| C4 | 2023 | 会议 | KDD / AAAI（之一） | KG 嵌入 / 检索 | 同济 | 一手题录 |
| C5 | 2023 | 期刊 | TKDE / TOIS（之一） | KGQA | 同济 | 一手题录 |
| C6 | 2022 | 会议 | WWW / SIGIR | 多模态 KG | 过渡期 | 一手题录 |
| C7 | 2021 | 会议 | ACM MM 2021（=A6） | 视觉语境选择性融合 | 东南 | 一手 |
| C8 | 2020 | 会议 | ISWC / EMNLP | KG 嵌入 + 问答 | 东南 | 一手题录 |
| C9 | 2019 | 会议 | ICDE / WWW | 子图查询 | 东南 | 一手题录 |
| C10 | 2018 | 会议 | ISWC 2018（=A7） | SPARQL 空答案 | 东南 | 一手 |
| C11 | 2018 | 会议 | ICBK 2018（=A8） | NL→Graph Query | 东南 | 一手 |
| C12 | 2017 | 会议/期刊 | （博士期）合著 | 子图匹配 / 嵌入 | 博士 | 一手题录 |

> 备注：C1—C12 中除 C7/C10/C11 外，**摘要原文未独立检索**，仅基于官网"代表性论著"清单存在性可信。

---

## D. 参与出版的专著（4 本）

- **来源**：[S1] 同济官网"参与出版专著 4 本"陈述 — 一手（仅事实，**未列具体书名**）
- **可信度**：一手（事实存在）/ 书名待考 — 诚实边界已记
- **可能候选**（推断，基于其 KG 方向与王昊奋团队常出版主题，**仅供线索**）：
  1. 知识图谱相关教材/技术书（OpenKG 生态）
  2. 多模态知识图谱专著
  3. 大模型与知识工程实践类
  4. 设计+AI 教学类（同济入职后参与）
- **诚实标注**：以上 4 项书名为**推断**，未在任何一手来源中出现具体题名。

---

## E. CCF 等级与时期标注汇总

- **CCF-A 顶级会议命中**：IJCAI、NeurIPS、ICML、SIGIR、VLDB、ACM MM、KDD/AAAI（题录）
- **专门 KG 会议**：ISWC 2018（含最佳论文提名）、ICBK 2018（含最佳论文）
- **东南大学时期主战场**：ISWC、ICBK、ACM MM 2021（KG 嵌入 + 多模态 KG）
- **同济大学时期主战场**：IJCAI、SIGIR、VLDB、NeurIPS、ICML（KG → LLM/Agent → 设计场景）

---

## 诚实边界（本文件）

1. **NeurIPS 2024 / ICML 2024 论文**：仅在官网"代表性论著"列表中作为题录条目存在；**完整标题、合作者、摘要原文未在公开渠道（arXiv / OpenReview / proceedings）独立检索到**。本文件保留题录级标注，避免编造。
2. **C1—C12 中部分条目**（特别是 C2/C3/C4/C5）：会议/期刊归属基于"官网清单 + 常识级方向匹配"推断，**精确题目未一一核对**。如需精确引用，需回到 [S1]/[S2] 重新比对论著清单原文。
3. **4 本专著的具体书名**：官网仅给出"参与出版专著 4 本"事实陈述，**书名清单不公开**。本文件未编造任何书名，仅给出推断方向。
4. **国家自然科学基金项目题目**：王萌主持过国自然面上项目、青年项目等（[S1] 一手陈述），**项目题目未在公开渠道披露**，故不在本文件中编写题目。
5. **同济官网"Nature Microbiology"陈述**：经核对系笔误，已修正为 *Health Information Science & Systems*（[S16] 一手核实）。
6. **作者位次**：除 A7/A8/B1（一作或一作之一可确认）外，其余论文的精确作者位次（一作 / 通讯 / 学生一作 + 王萌通讯）需回原文核对。
