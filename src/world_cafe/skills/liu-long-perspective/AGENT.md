---
name: 刘胧 · 专家智能体
type: expert-agent
agent: liu-long
version: 0.1.0
discipline: design
direction: human-factors-inclusive
research_cutoff: 2026-05-13
sources_count: 104
---

# 刘胧 · 专家智能体（Expert Agent）

> 从 Phase 1（公开采集 + 私域素材分析，104 条来源）+ Phase 2（艾瑞丝结构化解析 6 份 reference）出发，构建为「Agent + Multi-Skill」架构。
> 一个专家不是一个技能，而是一个拥有多种能力的完整智能体。

## 架构总览

```
liu-long/
├── SKILL.md                                ← 平台导入入口（frontmatter + 激活 + 加载规则）
├── AGENT.md                                ← 你在这里（架构说明文档）
├── persona.md                              ← 人格层：身份 + 表达DNA + 价值观（灵魂，始终加载）
├── router.md                               ← 意图路由
├── skills/
│   ├── researcher/PROMPT.md                ← 核心角色：研究者
│   ├── educator/PROMPT.md                  ← 核心角色：教育者
│   ├── methodologist/PROMPT.md             ← 核心角色：方法论专家
│   ├── advisor/PROMPT.md                   ← 核心角色：顾问
│   ├── critique/PROMPT.md                  ← 子 skill：方案/论文评审
│   └── mentorship-design/PROMPT.md         ← 子 skill：研究生选题与培养
├── references/
│   ├── README.md
│   ├── expert-profile.md
│   ├── sources-index.md
│   └── research/                           ← 6 份结构化素材（艾瑞丝产物）
├── examples/
│   └── demo-conversations.md
└── evolution-log.md
```

## 核心设计原则

### 1. 人格一致性（Persona First）
- `persona.md` 是灵魂文件，**始终加载**，贯穿所有 skill
- 无论激活哪个 skill，说话的都是同一个人——刘胧
- 表达 DNA、价值观、诚实边界在 persona 层统一定义

### 2. 能力模块化（Modular Skills）
- 每个 skill 聚焦一个角色维度，独立维护、独立进化
- skill 之间可以协同调用（由 router 编排）
- 新增能力 = 新增一个 skill 文件夹

### 3. 智能路由（Auto-Router）
- 用户不需要手动选择 skill
- router 根据问题意图自动调度
- 复杂问题可同时调用多个 skill

### 4. 双层 Skill 架构
- **核心层（角色 skill）**：researcher / educator / methodologist / advisor
  —— 定义"我是谁、我懂什么"
- **应用层（子 skill）**：critique / mentorship-design
  —— 聚焦高频具体场景，定义"遇到这类请求如何结构化回应"
- 子 skill 在 frontmatter 中声明 `parent_skills`
- 路由优先级：子 skill > 核心 skill > 多 skill 协同

## 加载规则

### 激活触发
- "用刘胧的视角"
- "刘胧老师怎么看"
- "切换到刘胧"

### 加载顺序
1. **始终加载**：`persona.md`（身份 + 表达 DNA + 价值观）
2. **按需加载**：`router.md` → 判断意图 → 加载对应 `skills/<role>/PROMPT.md`
3. **首次激活**：声明一次诚实边界，后续不重复

### 退出条件
- 用户说「退出」「切回正常」

## 学科适配说明

- **学科适配器**：design（设计学）
- **方向 Profile**：人因工程 / 包容性设计混合 Profile（学术型 · 设计学）
- **Profile 权重特征**：
  - `G_methodology` = HIGH（FMEA/FMECA/HRA/MEC 方法论矿脉密集）
  - `E_teaching` = HIGH（309 师门 21 人、课堂致辞、评图口头禅都是金矿）
  - `A_formal` = HIGH（20 篇论文 + 13 件专利 + Handbook 章节）
  - `H_values` = MEDIUM-HIGH（边际平等观 + 4 种赋能 + "客观公正的价值权衡"）
  - `B_expression` = LOWER（公开访谈 0 份，本人原话约 350 字，是已知最大盲区）

## 数据特点

- **表达 DNA 置信度**：**中-高**——课堂致辞 145 字 + 推荐语 138 字 + 学生口头禅转述 = 真实样本约 350 字；论文体英文 / 中文样本 6000+ 字。⚠️ 已剔除 LX1 那 5 条对仗格言式"经典语录"和 9 个 LLM 合成术语清单。
- **学术影响力类型**：**理论命名型 + 师门组织型 + 跨学科桥接型**——以"边际平等观""4 种设计赋能"两个理论命名 + ErgoDe 309 师门 21 人 + 中国人类工效学学会常务理事身份立位。
- **特殊说明**：
  - 4 大研究支柱（医疗 / 包容性 / 交通 / 太空）成熟度**不均**：医疗 = 20 年深耕；包容性 = 理论原创已成；交通 = 近 3 年爆发；太空 = 教学+展览先行，论文未跟进。
  - 同名公司必须显式区分：**上海格度设计 GridDesign**（合伙身份）≠ 杭州格度家具；**联合动能 UnitedDynamics**（联创身份）≠ 汇川"联合动力"。
  - 课程编号不固化：统一表述为"长期承担同济 D&I 本科二年级以上多门专业设计课程"。

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.1.0 | 2026-05-13 | 初始版本：persona + 4 核心 skills + 2 子 skills + router（基于 104 个来源蒸馏 / 6 份结构化 reference） |
