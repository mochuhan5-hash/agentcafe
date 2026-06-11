# 王萌 · 进化日志（Evolution Log）

> 本文档记录王萌 AI 专家视角的版本演化历史。

---

## v0.2.0 — 2026-05-15（**MAJOR · 架构重构**）

**变更类型**：MAJOR（架构重构 — persona 与 skills 的边界重新划分）

### 重构核心动机（用户原话）

> **「学者会有多篇论文、多个研究方向。任何一篇论文的标志性主张（哪怕是他被引用最多的那一篇）都不能放进 persona —— 因为 persona 是 agent 的默认人格，每次都会激活。一旦把某个学术论点放进 persona，agent 就会"不管用户问什么都往这个论点上扯"，把一个活生生的人变成一个论点复读机。」**
>
> **「这种观点至多是一个子 skill，说明他这个观点（按需加载，只有用户问到了类似问题，才能回答），不能放到专家人设里。」**

**v1 病灶诊断**：v0.1.0 把多篇不同论文的论点（神经+符号互补、视觉语境并非总是有帮助、永无止境的泛化、五级主动性、Rewrite+ReAct+Reflect 等）**全部塞进了 persona.md 的「核心心智模型 M1-M6」+「金句库 12 条」+「价值观与信念」三节**——这违反了"persona 是人 / skills 是论点"的根本原则。

### 重构 SOP

1. **艾瑞丝 v2 增量解析**（4 份新素材：[S28] / [S29] / [S30] / [S31]）输出 7 份 delta 文件
2. **艾瑞丝在 02-conversations.delta.md 末尾产出"塞吉视角候选 L3 三件套"** —— 跨东南/同济、跨 ≥ 3 处独立来源稳定的元思维三条（克制+反例驱动 / 跨学科翻译者 / 双维度矩阵化）
3. **塞吉 Step 0 重构方案** —— send_message 给主理人审；主理人确认后开始动笔
4. **persona 重写** —— 删除 v1 嵌入式具体论点，只保留跨阶段稳定特质 + 表达 DNA + 身份事实 + 诚实边界
5. **新增 4 个 perspective 子 skill** —— 把 v1 误塞进 persona 的论点全部下放
6. **核心 4 角色重写** —— researcher / methodologist 重写为元能力描述（虚拟情境演示，禁止指向具体论文）；educator / advisor 继承 + 轻调（移除案例调用清单中的具体论文论点引用 + 叠加 v2 同济期合作锚点）
7. **router 重构** —— 新增 Step 0 诚实边界拦截 + Step 1 元问题拦截 + Step 2 子 skill 优先匹配机制
8. **demo 改造** —— 在每组对话开头标注 router 加载链 + 新增 4 组路由验证对话（冷启动 / 能力元问题 / NS 触发 / 设计 LLM 触发）
9. **references 合并** —— v1 6 份 reference + v2 6 份 delta 共存形成完整 audit trail
10. **evolution-log + AGENT.md 更新** —— 记录重构原因 + 5 项 ISSUE 处置 + L3 三件套 ↔ S 编号对照矩阵

### 5 项 ISSUE 处置确认（艾瑞丝 parsing-issues.md → 用户裁决"按艾瑞丝建议全部采纳"）

| # | ISSUE | 处置位置 |
|---|---|---|
| **ISSUE-1** | NeurIPS 2024 / ICML 2024 主题归类与 v1 严重冲突（v1 错误归入"知识增强大模型"，实际为精确矩阵估计 / 联邦元迁移学习） | persona.md 诚实边界节 + AGENT.md L3 三件套 ↔ 证据矩阵节 + references/sources-index.md + research/01-writings.delta.md |
| **ISSUE-2** | v1「神经+符号」L3 顶级稳定 vs 同济期实际未复现 | persona.md 表达 DNA 节标注下放 + neural-symbolic-perspective.md 阶段标节明确"东南期 L3 → 同济期已变形 LLM × Symbolic × RAG" |
| **ISSUE-3** | v1 03-expression-dna 多个高频术语在 v2 新素材中 0 次复现（永无止境的泛化 / 变量的力量 / 葡萄汁等） | persona.md 表达 DNA 节明确下放 + neural-symbolic-perspective.md 论点 2-3 标"严格 L1，仅 [S19] 一处" |
| **ISSUE-4** | v1 高频术语「设计+AI 交叉」 vs 同济期已升级为「设计+技术+行为」三元 | persona.md 常用术语节并存两版本 + design-llm-perspective.md 论点 10 详细说明 |
| **ISSUE-5** | ACM MM 2021 论文位次确认 = 王萌一作（v1 未明确） | references/sources-index.md + multimodal-kg-perspective.md 论点 1 + AGENT.md 论文位次精确版 |

### v1 → v2 论点下放对照（已在 AGENT.md 详细列出）

**已下放到 perspective 子 skill 的 v1 内容**：

- v1 心智模型 M1（变量的力量 → 永无止境的泛化）→ `neural-symbolic-perspective.md`
- v1 心智模型 M2（选择性融合 / 视觉语境并非总是有帮助）→ `multimodal-kg-perspective.md`
- v1 心智模型 M3（神经+符号互补）→ `neural-symbolic-perspective.md`（明确标"东南期 L3，同济期已变形"）
- v1 心智模型 M4（嵌入是工具，查询是问题）→ `kg-research-perspective.md`（保留为 V2 用户场景驱动元能力的具体化）
- v1 金句 #1 视觉语境并非总是有帮助 → `multimodal-kg-perspective.md`
- v1 金句 #3 符号知识泛化来源于变量的力量 → `neural-symbolic-perspective.md`
- v1 金句 #5 阿司匹林反例 → `multimodal-kg-perspective.md`
- v1 金句 #6 神经+符号是未来 AI 重要方向 → `neural-symbolic-perspective.md`
- v1 金句 #7 葡萄汁有毒 → `neural-symbolic-perspective.md`
- v1 金句 #11 主动性双维度 → `kg-research-perspective.md`
- v1 methodologist 工具 1（Rewrite+ReAct+Reflect 完整步骤）→ `kg-research-perspective.md`
- v1 methodologist 工具 2（选择性融合门控完整步骤）→ `multimodal-kg-perspective.md`
- v1 methodologist 工具 3（空答案近似回退完整步骤）→ `kg-research-perspective.md`
- v1 methodologist 工具 5（个人 KG QA 工程骨架完整步骤）→ `kg-research-perspective.md`
- v1 researcher 7 个案例调用清单（阿司匹林 / 葡萄汁 / SPARQL 空答案 / 五级主动性 / NL→Graph Query / 个人 KG QA / VQFT）→ 各自分发到对应 perspective
- v1 educator 教学案例调用清单（神经+符号路线 2021→2024 延续等）→ 各自分发
- v1 advisor 案例（神经+符号路线一贯性）→ `neural-symbolic-perspective.md`

**保留 / 重构在 persona 的 v1 内容**：

- v1 心智模型 M5（双维度 × 多级框架）→ persona V3（跨阶段稳定 — 跨综述 + IJCAI + PPT 3 处稳定）
- v1 心智模型 M6（理论框架 + 工程落地成对）→ persona V4（研究审美底线，跨阶段稳定）
- v1 6 句式偏好 → persona 表达 DNA 节（删除内嵌反例例子，只保留句式骨架）
- v1 18 高频术语 → persona 常用术语节（重排 — 单篇论文术语下放，跨阶段术语保留 + 同济期 NEW 叠加）
- v1 5 禁忌词 → persona 禁忌词节（X-VAL + 同济期 NEW 2 条 T-6/T-7）
- v1 时间线 → persona 时间线节（叠加 v2 月级精度）
- v1 智识谱系 → persona 智识谱系节（叠加 v2 4 位新合作锚点 + 王毕伦链 + 蚂蚁链）
- v1 诚实边界 → persona 诚实边界节（叠加 v2 新发现的盲区）

### 产物清单（v0.2.0 完整文件树）

```
wang-meng/
├── SKILL.md (v0.2.0 重写)
├── AGENT.md (v0.2.0 重写 — 含 L3 三件套 ↔ S 编号对照矩阵 + v1→v2 论点下放对照)
├── persona.md (v0.2.0 重写 — 删除论点嵌入)
├── router.md (v0.2.0 重写 — 新增按需加载机制)
├── skills/
│   ├── researcher.md (v0.2.0 重写 — 4 元方法 + 虚拟情境演示)
│   ├── educator.md (v0.2.0 继承+轻调)
│   ├── methodologist.md (v0.2.0 重写 — 4 工作习惯 + 6 阶段 SOP 虚拟情境演示)
│   ├── advisor.md (v0.2.0 继承+轻调 — v2 同济期合作锚点叠加 + NEW 工具 4 复合身份选择矩阵)
│   ├── critique.md (v0.2.0 继承+小修 — 案例改路由提示)
│   ├── neural-symbolic-perspective.md (v0.2.0 NEW)
│   ├── multimodal-kg-perspective.md (v0.2.0 NEW)
│   ├── kg-research-perspective.md (v0.2.0 NEW)
│   └── design-llm-perspective.md (v0.2.0 NEW)
├── examples/
│   └── demo-conversations.md (v0.2.0 — 11 组：v1 9 组改造 + 2 组路由验证 NEW)
├── references/
│   ├── README.md (v0.2.0)
│   ├── expert-profile.md (v0.2.0 v1+v2 合并)
│   ├── sources-index.md (v0.2.0 — 35 条来源)
│   └── research/
│       ├── 01-writings.md (v1 基线，只读)
│       ├── 01-writings.delta.md (v2 增量)
│       ├── 02-conversations.md (v1 基线，只读)
│       ├── 02-conversations.delta.md (v2 增量 — 含塞吉视角候选 L3 三件套)
│       ├── 03-expression-dna.md (v1 基线，只读)
│       ├── 03-expression-dna.delta.md (v2 增量)
│       ├── 04-external-views.md (v1 基线，只读)
│       ├── 04-external-views.delta.md (v2 增量)
│       ├── 05-decisions.md (v1 基线，只读)
│       ├── 05-decisions.delta.md (v2 增量 — 含 NEW 决策节点 #6 同济期产品化)
│       ├── 06-timeline.md (v1 基线，只读)
│       └── 06-timeline.delta.md (v2 增量)
└── evolution-log.md (v0.2.0 — 本文件)
```

### v0.2.0 三反问自检结果（交付前必跑）

1. **「删掉 wang-meng 这个名字，persona.md 还能认出是王萌吗？」** ✅ **YES**
   - 跨学科翻译者 + 克制+反例+分场景论证 + 双维度矩阵化 三大特质极具辨识度
   - 同济期"我就是这个产品的直接客服"+ 自嘲式现实约束叙事（baby learning 头盔被抵制）独有
2. **「如果用户只是问『你是谁』，agent 会主动扯到神经+符号或视觉语境并非总是有帮助吗？」** ✅ **NO**
   - persona 首次交互模板 + router Step 1 元问题拦截 + demo 示例 8 路由验证均已确保
   - 自我介绍只说"KG/LLM × 设计学的跨学科翻译者"+"克制+反例+分场景论证的研究风格"
3. **「如果用户问『多模态 KG 怎么做』，agent 才会激活 multimodal-kg-perspective 子 skill 吗？」** ✅ **YES**
   - router Step 2.2 perspective 子 skill 优先匹配机制 + demo 示例 1, 5, 6 多次验证

### 表达 DNA 统计（v0.2.0）

- **句式骨架**：6 类 X-VAL（S-1 ~ S-6）+ 4 类同济期 NEW（S-7 ~ S-10）= **10 类**
- **高频术语**：12 个跨阶段稳定 + 14 个同济期 NEW = **26 个**（其余下放到 perspective 子 skill）
- **该场景金句库**（在 4 个 perspective 内）：neural-symbolic 6 条 + multimodal-kg 6 条 + kg-research 5 条 + design-llm 6 条 = **23 条**
- **禁忌词**：5 条 X-VAL（T-1 ~ T-5）+ 2 条同济期 NEW（T-6 / T-7）= **7 条**

### 跨阶段稳定 L3 三件套（v0.2.0 核心）

| L3 特质 | 跨阶段证据 | 跨场景证据数 |
|---|---|---|
| **L3-A 克制+反例驱动+分场景论证** | [S19]/[S28]/[S29]/[S30]/[S31] | **4 处独立来源稳定** |
| **L3-B 跨学科翻译者** | [S29]/[S30]/[S31] | **3 处独立来源稳定** |
| **L3-C 双维度矩阵化思考** | [S22]/[S10]/[S30] | **3 处独立来源稳定** |

### 架构决策记录（v0.2.0 核心）

1. **persona = 人，skills = 论点（铁律）**：v1 把"心智模型"+"金句库"+"价值观信念"全塞进 persona 是结构错误；v2 严格分离
2. **perspective 子 skill = 按需加载知识包（v2 新架构）**：与 critique（结构化输出型）不同，perspective 是「领域论点知识包」——触发条件 + 不触发处理 + 论点 + 证据 + 金句 + 反例 + 用法注意 七节式
3. **核心 4 角色 = 元能力描述**：researcher / educator / methodologist / advisor 内部**禁止**嵌入具体论点；所有具体论点路由到 perspective 子 skill
4. **demo 必须显式标注 router 加载链**：每组对话开头标 `[路由加载]: [persona + ...]`，让审计者能验证按需加载机制
5. **L3 三件套替代 v1 6 心智模型**：v1 用「6 个心智模型 M1-M6」做证据矩阵，但 M1/M2/M3 实为单篇论文论点；v2 改用艾瑞丝实证的 L3 三件套（V1 + V2 + V3）+ 元能力补充（V4 + V5）共 5 条
6. **v1 reference 只读，v2 delta 共存**：保持 audit trail 完整，让审计者可以看到每条修订的依据

### 自检清单打勾结果

- ✅ 命名三件套与 v0.1.0 完全一致（expert_display_name=王萌 / expert_slug=wang-meng / expert_fields 4 项）
- ✅ 文件树结构合规（SKILL.md / AGENT.md / persona.md / router.md / skills/ / examples/ / references/ / evolution-log.md 全齐）
- ✅ persona.md 含 5 个 ### 核心观点子项（落在 quality_check 3-7 范围）
- ✅ AGENT.md 含完整 ASCII 文件树 + frontmatter（name / type / version）+ researcher 描述
- ✅ router.md 三层结构（子 skill 优先 / 核心角色 / 多 skill 协同）+ 触发条件 + fallback + 7 个具体示例
- ✅ 4 个 perspective 子 skill frontmatter 全含 `parent_skills`
- ✅ critique 子 skill frontmatter 含 `parent_skills: [researcher, educator]`
- ✅ demo-conversations.md 含 11 组（≥ 7 标准）
- ✅ references 三件套齐全（README / expert-profile / sources-index）
- ✅ research/ 12 份齐全（v1 6 + v2 6 delta）
- ✅ 三反问自检全部通过

### v0.2.0 v1 既有路径处置

⚠️ **绝对不触碰** `/Users/txzxszhang/Desktop/DistillationTest/wang-meng/`（v1 路径） — v0.2.0 全部产出在 `/Users/txzxszhang/Desktop/DistillationTest/wang-meng-intake/distilled/wang-meng/`，便于主理人最后做 diff 对比、审定后再决定是否合并到 v1 路径。

---

## v0.1.0 — 2026-05-12（初始版本）

**变更类型**：MAJOR（架构首建）

### 建构来源

- **阿特拉斯**（爬取）：4 轮爬取 → 27 个 S 编号一手 / 二手来源 + 4 个乐享私域 L-S 编号 + 2 个已排除 X 编号
- **艾瑞丝**（解析）：6 份结构化 reference（01-writings / 02-conversations / 03-expression-dna / 04-external-views / 05-decisions / 06-timeline）
- **塞吉**（蒸馏）：完整 Agent 文件树（v0.1.0）

### 产物清单（v0.1.0）

- `SKILL.md` / `AGENT.md` / `persona.md` / `router.md`
- `skills/researcher.md` / `educator.md` / `methodologist.md` / `advisor.md` / `critique.md`
- `examples/demo-conversations.md`（9 组）
- `references/README.md` / `expert-profile.md` / `sources-index.md`
- `references/research/`（艾瑞丝 6 份原始解析文件）

### 心智模型三重验证结果（v0.1.0 — v0.2.0 已重构）

| 模型 | v0.1.0 结果 | v0.2.0 处置 |
|------|-----|-----|
| M1 变量的力量 → 永无止境的泛化 | ✅ 通过 | **下放** neural-symbolic-perspective |
| M2 选择性融合 | ✅ 通过 | **下放** multimodal-kg-perspective |
| M3 神经 + 符号互补 | ✅ 通过 | **下放** neural-symbolic-perspective（明确"东南期 L3，同济期已变形"） |
| M4 嵌入是工具，查询是问题 | ✅ 通过 | **下放** kg-research-perspective + 保留为元能力 V2（用户场景驱动） |
| M5 双维度 × 多级框架 | ✅ 通过 | **保留为 persona V3** |
| M6 理论框架 + 工程落地成对 | ✅ 通过（弱排他，已标注局限） | **保留为 persona V4** |
| M7 以人为中心 + 设计场景下沉 | ⚠️ 降级为决策启发式 | v0.2.0 进一步下放 design-llm-perspective |

---

## 未来版本规划（草案，非承诺）

### v0.3.x — 内容补充

- 🟡 王毕伦合作链机构 / 职务背景查证（v0.2.0 盲区）
- 🟡 蚂蚁集团合作链合作单位独立确认（v0.2.0 推断）
- 🟡 AI-Ceping 平台 URL / 出处论文（[S30] PPT p15 仅给数字）
- 🟡 TT 设计学院精确上线日期 + 当前用户数
- 🟡 王萌对 o1 / o3 推理大模型的 NS 视角公开评论
- 🟡 灵感口袋（TT Pocket）的具体交互范式
- 🟡 大设计大模型 vs 大模型知识引擎是否同一项目（[L-S3] vs [S30] 命名差异）

### v0.4.x — 新增子 Skill（如有需要）

- 🔵 `workshop-designer.md` — 产学研项目启动方案子 Skill（如素材充足）
- 🔵 `career-compass.md` — 学者转轨咨询子 Skill（如访谈补充）
- 🔵 设计 + LLM 子方向细分 perspective（如垂域炼制 / 设计师工作流采集 / 隐性知识转化各自单独 perspective）

### v1.0.0 — 正式版（需）

- 王萌本人审阅确认
- 真实用户测试反馈 ≥ 10 组
- 学术型 + 设计学跨学科 Profile 适配器正式发布

---

## 变更类型说明

- **MAJOR（x.0.0）**：架构变更（增删核心 Skill / 子 Skill / 适配器变更 / persona-skills 边界重划）
- **MINOR（0.x.0）**：内容变更（新增知识、调整路由规则）
- **PATCH（0.0.x）**：小修补（修正事实错误、补充证据）
