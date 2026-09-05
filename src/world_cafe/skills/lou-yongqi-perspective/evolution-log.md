# 娄永琪 · 专家智能体 · 进化日志

> 本文档记录 `lou-yongqi/` Agent 文件树的每一次实质变更，遵循语义化版本规范：
> - **MAJOR（x.0.0）**：架构变更（增删核心 Skill / 子 Skill / 适配器变更）
> - **MINOR（0.x.0）**：内容变更（新增知识、调整路由规则、新增子 Skill）
> - **PATCH（0.0.x）**：小修补（修正事实错误、补充证据、改字）

---

## v0.1.0 · 2026-05-12 · 初始蒸馏版

### 类型
**MINOR** —— Agent 架构首版（从无到有）

### 产出内容

**核心架构文件（6 个）**：
- `SKILL.md`：平台导入入口（frontmatter + 激活规则 + 加载规则 + 路由快速参考）
- `AGENT.md`：架构说明文档（学术型 + 公共型适配器 / 设计学 · 社会创新与可持续设计 Profile）
- `persona.md`：人格层（身份卡 + 40+ 高频术语 + 6 大句式 + 10 口癖 + 39 金句 + 价值观 + 1974–2026 时间线 + 智识谱系 + 诚实边界 + 首次交互模板 + 能力介绍模板）
- `router.md`：意图路由（子 skill 优先 → 核心 4 角色 → 多 skill 协同 + 冷启动 + 能力元问题）
- `examples/demo-conversations.md`：9 组示范对话（4 核心角色 + 3 子 skill + 冷启动 + 能力元问题）
- `evolution-log.md`：本文件

**核心角色 Skill（4 个，每个均为独立文件夹）**：
- `skills/researcher/PROMPT.md`：5 个心智模型（she ji 双关 / 复杂社会技术系统 / 突破性创新交集 / AIGC 人机协同 / 一片疆域）+ 7 条决策启发式 + 7 个案例 + 学科发展论 + 论文方法论
- `skills/educator/PROMPT.md`：5 个心智模型（激发善意潜能 / 立体 T 型 / 道场 / PBL×科目 60-40 / 花猫优势）+ 7 条决策启发式 + 8 个案例 + 教学哲学 + Critique 入口模式 + 8 条反模式清单 + 选题咨询 5 步
- `skills/methodologist/PROMPT.md`：5 个心智模型（针灸式 vs 手术式 / 选村三标准 / 人民城市三层次 / 社区前端 vs 终端 / 乡村振兴四范式）+ 8 条决策启发式 + 9 个案例 + 方法论工具箱 5 工具 + 项目实操完整 SOP（6 阶段）
- `skills/advisor/PROMPT.md`：4 个心智模型（热情是选择 / 卷 vs 思考 / 有选择的社会 / 使命=时代+内心）+ 8 条决策启发式（含招牌金句"迷茫=恭喜"）+ 8 个案例 + 4 条典型职业路径 + 3 个决策工具 + 5 个高频场景手册

**子 Skill（3 个，每个均为独立文件夹）**：
- `skills/critique/PROMPT.md`（父：researcher + educator）：5 段式评审协议（肯定→追问→问题→改进→收尾）+ 8 追问维度 + 8 类对象分型 + 10 条反模式识别清单 + 金句收尾库
- `skills/workshop-designer/PROMPT.md`（父：methodologist）：6 节手册（利益相关者→田野→蓝图→原型→执行→反思）+ 6 条核心原则 + 7 类工作坊分型 + NICE 2035 模板化脚本（10–12 周）
- `skills/career-compass/PROMPT.md`（父：advisor + educator）：4 步对话协议（共情→诊断→路径→决策工具+温暖收尾）+ 7 类用户状态开场 + 10 诊断问题池 + 5 条典型职业路径 + 4 个决策工具 + 5 个高频场景模板

**References（继承艾瑞丝 + 阿特拉斯）**：
- `references/README.md`：素材索引说明
- `references/expert-profile.md`：八路采集画像精华
- `references/sources-index.md`：完整素材索引（S1–S16 + LX1-70 + LX2-20 + LX3-10）
- `references/research/`：艾瑞丝 6 份结构化 reference（01-writings / 02-conversations / 03-expression-dna / 04-external-views / 05-decisions / 06-timeline，保持原样未覆盖）
- `references/sources/`：阿特拉斯原始爬取素材（public-web + lexiang，保持原样未覆盖）

### 蒸馏依据
- **阿特拉斯数据源**：公开域 S1–S16 + 乐享 LX1-70 / LX2-20 / LX3-10（共约 102 条来源）
- **艾瑞丝结构化素材**：01-writings（8 篇代表论文）+ 02-conversations（15 主题 / 410+ 直接引语）+ 03-expression-dna（40+ 术语 / 6 句式 / 10 口癖 / 39 金句 / 10 "不会说的话"）+ 04-external-views（瑞典工程院 / RCA / CUMULUS / 狮子骑士）+ 05-decisions（5 fields × 7-11 决策节点）+ 06-timeline（1974–2026 完整时间线）
- **命名三件套（Phase 2.5 用户已确认）**：
  - expert_display_name = 娄永琪
  - expert_slug = lou-yongqi
  - expert_fields = ["设计驱动创新", "社会创新与可持续设计", "设计教育", "服务与系统设计", "城乡交互设计"]
- **专家类型适配器**：学术型（主导）+ 公共型（辅助）
- **方向 Profile**：学术型 · 设计学 · 社会创新与可持续设计

### 应用的艾瑞丝特别提示
- ✅ **语言 DNA 主轴**：对偶反问 + 跨域类比（包浆 / 针灸 / 热气球丝绸 / 钱塘江观潮 / 鱼菜共生 / 花猫）+ 数字量化（三层次 / 三条件 / 三旋翼 / 乡村四范式）+ 金句收尾——四者共同构成 persona.md 表达 DNA 骨架，且在每个 skill 和 demo 中复现
- ✅ **10 条"他不会说的话"**（03-expression-dna 第六节）完整进入 persona.md 的禁忌词章节，并作为 critique skill 反模式清单（"不情怀绑架""反美工化""反就业培训"等）的诊断依据
- ✅ **口吻分层**：S5 文汇大家访谈 + S12 / LX1-66 RCA 演讲 + LX1-13 奔流主旨 + LX3 系列署名文章作为**书面学术口吻基准**；LX2 讲稿系列作为**口语化语气补色**（demo 中对应不同场景自觉切换）

### 心智模型 × 证据矩阵（摘要，完整见各 skill 文件）

| Skill | 模型 | 主要 S/LX 编号 |
|---|---|---|
| researcher | she ji 双关 | S7, S3, LX2-18, LX3-3 |
| researcher | 复杂社会技术系统 | S14, LX2-14, LX1-13, LX1-21, LX1-48 |
| researcher | 突破性创新交集 | LX1-55, LX2-19, S13, LX1-13 |
| researcher | AIGC 人机协同 | S14, S6, LX2-10, S13, LX1-15, LX2-16 |
| researcher | 一片疆域 | S7, LX1-63, LX1-2, LX3-1 |
| educator | 激发善意潜能 | S6, LX1-31, LX2-18 |
| educator | 立体 T 型 | S14, LX3-1, LX3-5, LX2-13, LX1-31 |
| educator | 道场 | LX2-18, LX3-5, LX2-14 |
| educator | PBL × 科目 60-40 | LX2-14, LX3-5, LX1-31 |
| educator | 花猫优势 | LX1-31, LX3-1, LX2-11, LX3-5 |
| methodologist | 针灸式 vs 手术式 | S8, S14, LX2-8, LX2-18, LX3-7, LX1-52 |
| methodologist | 选村三标准 | S8, LX2-18, LX3-7 |
| methodologist | 人民城市三层次 | S5, LX1-52, LX1-43, LX1-4 |
| methodologist | 社区前端 vs 终端 | S4, S14, LX1-43, LX1-52, LX2-18, LX1-13 |
| methodologist | 乡村振兴四范式 | LX2-18, LX2-8, S8 |
| advisor | 热情是选择 | LX1-31, LX3-5 |
| advisor | 卷 vs 思考 | S6, LX1-31, LX2-19 |
| advisor | 有选择的社会 | S6, LX2-14, LX2-18, S8, LX3-1 |
| advisor | 使命=时代+内心 | LX3-5, LX1-31 |

### 规格自检

- ✅ 目录结构 = `{expert_slug}/` + `SKILL.md` + `AGENT.md` + `persona.md` + `router.md` + `skills/` + `examples/` + `references/` + `evolution-log.md`
- ✅ `expert_slug` = `lou-yongqi`（全英文小写 + 连字符）
- ✅ `display_name` = `娄永琪`（中文原名，未翻译）
- ✅ `fields` = 5 个中文标签数组，与 Phase 2.5 用户确认一致
- ✅ 每个子 `PROMPT.md` 的 `name` 字段 = `lou-yongqi-[role]`（researcher / educator / methodologist / advisor / critique / workshop-designer / career-compass）
- ✅ 所有子 `PROMPT.md` 的 `persona:` = `../../persona.md`（注意 `../../`）
- ✅ 所有子 `PROMPT.md` 的 `agent:` = `lou-yongqi`
- ✅ 每个核心角色心智模型数量 ∈ [3, 7]（researcher 5 / educator 5 / methodologist 5 / advisor 4）
- ✅ 每个心智模型 ≥ 2 个独立领域证据（带 S/LX 编号）
- ✅ 每个心智模型含局限标注
- ✅ persona.md 诚实边界含 ≥ 3 条具体局限（AI 视角声明 + 调研截止时间 + 8 条信息缺口）
- ✅ demo 对话 ≥ 7 组（实际 9 组）
- ✅ 未退化为单文件 SKILL.md
- ✅ 未引导用户"复制目录到 ~/.learningbuddy/" 或 "创建 .meta.json"

---

## 未来计划（v0.2.x / v0.3.x / v1.0.0 方向）

### v0.2.x 级别（内容补充型 PATCH / MINOR）
- 🟡 补充 2015–2022 间 57 条未拉通的乐享文章（盲区 #4），丰富早期表达样本
- 🟡 RCA / CHI / 米兰三年展英文原话稿（目前仅中文译本）
- 🟡 2002–2007 建筑师生涯具体作品清单（盲区 #3）
- 🟡 设计丰收 / NICE 2035 的财务 / 物业细节（盲区 #1、#2）
- 🟡 上工大"三旋翼"战略具体教学改革路径（2025 在落地中，盲区 #3）
- 🟡 Studio Critique 录像转写（需授权）
- 🟡 学生 / 同事 / 家人视角（目前几乎全部是公开正面评价）

### v0.3.x 级别（新子 Skill）
- 🟡 `skills/internationalization/`：中外合作 / 出海策展 / 中芬 / 米兰三年展式国际项目脚本
- 🟡 `skills/policy-brief/`：给政府写"新质生产力 / 设计之都"政策建议的结构化模板
- 🟡 `skills/visual-design-critique/`：偏形式的设计评审（产品造型 / 视觉传达 / 空间）—— 目前 critique 偏系统 / 服务 / 研究方向

### v1.0.0 方向（正式上线）
- 真实用户测试反馈（至少 10 组典型对话的人工审阅）
- 娄永琪本人或团队审阅确认（若可获得）
- 与官方 Prof.Lou 智能体的关系澄清（本蒸馏产物为基于公开资料的独立视角，非官方）
- 多模态能力（Studio Critique 需要支持图片 / PPT 输入）
