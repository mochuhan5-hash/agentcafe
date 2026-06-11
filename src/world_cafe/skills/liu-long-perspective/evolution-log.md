---
agent: liu-long
expert_display_name: 刘胧
last_updated: 2026-05-13
---

# 刘胧 · 进化日志（Evolution Log）

> 记录每一次蒸馏 Agent 的版本变更。版本策略遵循 SemVer：
> - **MAJOR**：架构变更（增删核心 Skill / 子 Skill / 适配器变更）
> - **MINOR**：内容变更（新增知识、调整路由规则）
> - **PATCH**：小修补（修正事实错误、补充证据）

---

## v0.1.0 · 2026-05-13 · 初始蒸馏（MAJOR）

### Phase 1（爬取，阿特拉斯）
- 完成 104 条公开素材采集（S1-S40 + LX3 全 20 篇论文 PDF + LX4 全 13 件专利 PDF + LX5 / LX5_extra 学院公众号 / 学生致谢 / 课程报道）
- 实锤剔除 S9 网易公开课（实为清华饶培伦的课）
- 实锤剔除 LX1 5 条"经典语录" + 9 个"高频术语"清单（强疑 LLM 合成草稿）
- 锁定同名公司澄清：上海格度设计 GridDesign（合伙）≠ 杭州格度家具；联合动能 UnitedDynamics（联创）≠ 汇川"联合动力"

### Phase 1.5 / 2.5 用户确认门
- ✅ 命名三件套确认：
  - `expert_display_name = 刘胧`
  - `expert_slug = liu-long`
  - `expert_fields = ["人因工程", "包容性设计", "设计学", "用户研究"]`
- ✅ 学科适配器：学术型 · 设计学
- ✅ 方向 Profile：人因工程 / 包容性设计混合（学术型 · 设计学）

### Phase 2（结构化解析，艾瑞丝）
落盘 6 份 reference 至 `references/research/`：
- `01-writings.md`（293 行 · 4 大支柱论文 + 装饰摘要）
- `02-conversations.md`（279 行 · ⭐ 课堂致辞 145 字 + 推荐语 138 字 + ErgoDe 实锤）
- `03-expression-dna.md`（245 行 · ⭐ 真实高频词 vs LX1 对比 + 5 句式 + 7 维风格光谱 + 不会说的话）
- `04-external-views.md`（311 行 · 学生评价 + 309 同门 21 人 + 4 国国际合作者）
- `05-decisions.md`（188 行 · 4 大支柱决策节点）
- `06-timeline.md`（247 行 · 1989-2026 + 4 层协作网络 + 13 专利）

### Phase 3（蒸馏，塞吉）

#### 落盘文件清单
| 文件 | 功能 |
|------|------|
| `SKILL.md` | 平台导入入口 + 激活 + 加载规则 |
| `AGENT.md` | 架构说明文档 |
| `persona.md` | 灵魂文件：身份 + 表达 DNA + 价值观 + 诚实边界 |
| `router.md` | 意图路由：4 核心 + 2 子 Skill + 越界处理 |
| `skills/researcher/PROMPT.md` | 5 个心智模型 + 7 条决策启发式 + 11 个案例 + 学科发展论 |
| `skills/educator/PROMPT.md` | 4 个心智模型 + 8 条启发式 + 8 个案例 + Critique 模式 + 8 反模式识别 + 选题引导框架 |
| `skills/methodologist/PROMPT.md` | 4 个心智模型 + 7 条启发式 + 5 大方法论工具（FMECA / MeX 6 节手册 / 信任校准实验 / MEC / scoping+实证） |
| `skills/advisor/PROMPT.md` | 3 个心智模型 + 6 条启发式 + 5 条职业路径 + 3 决策辅助工具 + 6 高频场景手册 |
| `skills/critique/PROMPT.md` | 5 段式评审 + 7 类对象分型 + 8 类反模式识别 + 评图三层 / 看图四步法 |
| `skills/mentorship-design/PROMPT.md` | 4 步协议 + 4 大支柱地形图 + 3-5 年培养路径 + 反馈节拍 + 师门生态地图 |
| `examples/demo-conversations.md` | 9 组示范对话（4 核心角色 + 2 子 Skill + 冷启动 + 元问题 + 概念辨析） |
| `references/README.md` | 素材索引说明 |
| `references/expert-profile.md` | 八路采集画像精华（A 产出 / B 表达 / C 实践 / D 批评 / E 教学 / F 网络 / G 方法 / H 价值观） |
| `references/sources-index.md` | 完整素材索引（S1-S40 + LX3 全 20 + LX4 全 13 + LX5 系列） |
| `references/research/01-06.md` | 艾瑞丝 6 份结构化产物（不修改） |
| `evolution-log.md` | 你在这里 |

#### 心智模型矩阵（4 核心 Skill 共 16 个）

| Skill | 心智模型数 | 核心模型 |
|-------|-----------|---------|
| researcher | 5 | 四元交互框架（SHEL）/ 边际平等观 / 4 种设计赋能 / 信任 × 错误偏置 × 透明度 / 医疗共创 AI 跃迁 |
| educator | 4 | 肯定-推动-留白反馈节拍 / 评图三层 / 学术型人因人 / 师门生态 309 |
| methodologist | 4 | FMECA 工程血脉 / MeX 三方协同 / 4 种赋能（实操工具箱）/ 信任校准实验设计 |
| advisor | 3 | 学术 + 产业双轨身份 / 4 大支柱 = 4 条产业落地路径 / 309 师门是输送平台 |

每个心智模型都有 ≥2 个独立来源验证。

#### 子 Skill 列表（最终生成 2 个，符合主理人建议中"最多 2-3 个"）

- `critique` —— 方案 / 论文评审（父 = researcher + educator）
- `mentorship-design` —— 研究生选题与培养（父 = educator + advisor）

未生成的子 Skill：
- ⛔ workshop-designer —— methodologist 的 MeX 6 节手册已经够用
- ⛔ career-compass —— advisor 的 5 条职业路径 + 6 高频场景手册已经够用
- ⛔ course-design —— 太空 / 飞梭智行 / 医疗共创课程组指导经验已分布在 educator + mentorship-design + 案例清单中，独立子 Skill 价值不够

#### 6 大铁则落实情况（persona.md）

- ✅ 表达 DNA 直接落实艾瑞丝 03 真实样本（已剔除 LX1 那 5 条 + 9 个伪术语）
- ✅ 同名公司显式区分（GridDesign / UnitedDynamics 在 persona / advisor / router 三处声明）
- ✅ 课程编号不固化（统一表述"长期承担同济 D&I 本科二年级以上多门专业设计课程"）
- ✅ 4 大研究支柱（医疗 / 包容性 / 交通 / 太空）成熟度差异显式标注
- ✅ 2 大理论原创（边际平等观 + 4 种赋能）作为 researcher 心智模型核心
- ✅ 智识谱系（TU Kaiserslautern / 同济董华 / Hua Dong / Hoelscher / Butz / Clarkson / 309 师门）完整

#### 诚实边界标注（persona.md §诚实边界）

显式标注的盲区：
- ❌ 个人生活 / 家庭信息（超界禁区，永不补充）
- ❌ 本人公开社交账号（实证无）
- 🟡 2016 同济国际会议特邀报告全文（仅题目）
- 🟡 博士论文题目 / Dr.-Ing. 答辩具体年份
- 🟡 完整论文全集（2007-2014 中文小论文可能漏抓）
- 🟡 太空主线 SCI/EI 论文（截止时点尚无）
- 🟡 ResearchGate 2,187 vs ScholarMate 1,454 被引差异（并列呈现）
- 🟡 LX1 自陈 6 家全球企业咨询（仅作"据其个人简历自陈"转述）

#### 三重验证（每个心智模型必过）

按元框架第九章：
- 跨域复现（≥2 不同领域 / 场景出现）：✅ 全部 16 个心智模型通过
- 生成力（能推断对新问题的可能立场）：✅ 全部通过
- 排他性（不是所有同行专家都这样想）：✅ 全部通过

无需降级或丢弃任何模型。

---

## 计划中（v0.2.0+）

### v0.1.1 · 2026-05-14 · 运行时评测后优化（PATCH）

基于 45 题 × 9 Agent 运行时评测（综合 4.72/5.0），针对以下问题进行优化：

#### 改动清单

| 文件 | 改动 | 解决问题 |
|------|------|---------|
| `persona.md` §回答行为规则 #3 | 收尾从 2 选 1 → **5 选 1 变体轮换池** + "连续 3 次不重复"规则 | 收尾"比之前好但还不够好"占 100% 过于集中 |
| `persona.md` §回答行为规则 #6 | 新增**回答长度控制**（冷启动 200-400 / 研究类 600-1200 / 顾问类 400-800 / 边界拒绝 100-250） | 回答长度差异大（critique ~1000 vs advisor ~400） |
| `persona.md` §回答行为规则 #7 | 新增**术语频控规则**（"半步移动"仅选题场景 / 单次不超 2 次） | "半步移动"49% 回答出现，非选题场景勉强 |
| `persona.md` §回答行为规则 #8 | 新增**幽默触发规则**（条件 + 方式 + 示例 + 频率建议） | 45 题幽默元素几乎未触发 |
| `router.md` §冷启动引导 | 新增**免责声明严格规则**（仅整个会话首次 + 4 条禁止规则） | 多 Skill 协同场景重复输出免责声明 |

#### 评测结果摘要

- 综合评分：4.72 / 5.0
- 最高分 Skill：critique 4.9 / researcher 4.9
- 禁忌词违反：0/45 ✓
- 边界控制：5/5 全部正确
- 与娄永琪 Skill 对比：知识准确性 +0.1 / 专业深度 +0.1 / 交互体验 -0.2

---

### v0.2.x 内容补充
- 🟡 让用户提供 CV 原件确认 LX1 自陈 6 家全球企业咨询列表
- 🟡 用户提供 2016 同济国际会议特邀报告 PPT / 摘要
- 🟡 CNKI 全量校核 2007-2014 中文小论文
- 🟡 太空主线 SCI/EI 论文跟进时再补 researcher / methodologist 案例

### v0.3.x 真实用户反馈迭代
- 等待平台试聊 + 发布后的真实反馈
- 重点观察评图（critique）和选题引导（mentorship-design）两个子 Skill 的命中率

### v1.0.0 正式上线
- 通过真实用户验证 + 专家审阅确认（如可触达）
