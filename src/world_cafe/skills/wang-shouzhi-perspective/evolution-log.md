# 王受之专家智能体 · 进化日志（evolution-log）

> 记录本智能体的每一次架构变更、内容迭代、外部反馈处理。
> 版本号遵循 SemVer：**MAJOR**（架构变更）/ **MINOR**（内容变更）/ **PATCH**（小修补）。

---

## v0.1.0 · 2026-05-13 · 蒸馏出炉初版

### 调研背景

- **调研日期**：2026-05-12 ~ 2026-05-13
- **数据源数量**：**546 条**（540 本地素材 + 6 SN 增量）
  - priority/ 9 篇视频 ASR（28.9 万字 / 2011-2023 跨 12 年）
  - peer_reviews/ 8 篇深访（3.05 万字 / 2012-2026 跨 14 年）
  - wechat 458+14 篇自媒体 + 长江亲撰
  - blog 21 篇新补正文 + 8 篇原（4.0 万字）
  - books/ 18 章核心章节（47.7 万字 / 仅供事实校准）
  - SN001-006 增量来源（2018 / 2020 / 2026-Q1Q2）
- **总字数**：约 111 万字
- **时间跨度**：2002-2026 公开素材 / 1946-2026 时间线

### 团队链路

- **阿特拉斯**（爬取）：完成 540 一手素材 + 6 SN 增量爬取，编制完整 S 编号映射（`crawl-report.md` § 3.1）
- **艾瑞丝**（解析）：交付 7 份结构化解析文件
  - `00-sources-index.md` — S001-S540 + SN001-006 价值定位
  - `01-writings.md` — 9 部代表作 + 系统性论文
  - `02-conversations.md` — 8 主题引语池
  - `03-expression-dna.md` — 24 高频术语 + 8 句式 + 10+ 口癖 + 35 金句 + 5 类幽默 + 3 段节奏样本 + 反向语库
  - `04-external-views.md` — 含人格戏剧张力专论
  - `05-decisions.md` — 8 个领域 + 4 个人生转折点
  - `06-timeline.md` — 完整时间线 + S 编号详注
- **主理人**：Phase 2.5 决议固化（命名三件套 / 8 Skill 架构 / D1-D4 决议）
- **塞吉**（蒸馏）：Phase 3 产出本智能体

### 产出清单

```
wang-shou-zhi/
├── SKILL.md                                ✅ 智能体平台导入入口
├── AGENT.md                                ✅ 架构说明
├── persona.md                              ✅ 灵魂文件（含 24 高频术语 / 8 句式 / 10+ 口癖 / 35 金句 / 5 类幽默 / 3 段节奏样本）
├── router.md                               ✅ 意图路由（Step 0-3 完整三层 + 冷启动 + 模糊意图 + 能力元问题）
├── skills/
│   ├── researcher/PROMPT.md                ✅ 5 心智模型 / 7 启发式 / 9 案例
│   ├── educator/PROMPT.md                  ✅ 5 心智模型 / 8 启发式 / 8 案例 / 8 反模式 / Critique 模式
│   ├── methodologist/PROMPT.md             ✅ 5 心智模型 / 7 启发式 / 8 案例 / 4 工具箱
│   ├── advisor/PROMPT.md                   ✅ 5 心智模型 / 8 启发式 / 10 案例 / 留学决策树 + 阅读路线 + 6 选校 + 10 高频场景
│   ├── critique/PROMPT.md                  ✅ 5 段式标准输出 / 7 类作品分型 / 8 反模式
│   ├── design-history-storyteller/PROMPT.md ✅ 六幕脚本 / 3 段节奏样本 / 14 故事素材库
│   ├── painter/PROMPT.md                   ✅ ≥4 条局限标注（D2 决议）/ 4 段画家自述 / 8 故事素材库
│   └── real-estate-advisor/PROMPT.md       ✅ ≥4 条局限标注（D2 决议）/ 4 步住宅区分析 / 9 项目素材库
├── examples/
│   └── demo-conversations.md               ✅ 10 组对话（核心 4 + 应用 4 + 冷启动 + 能力元问题）
├── references/
│   ├── README.md                           ✅
│   ├── expert-profile.md                   ✅ 八路（A-H）画像精华
│   └── sources-index.md                    ✅ 完整 S 编号映射（继承阿特拉斯）
└── evolution-log.md                        ✅ 你在这里
```

**累计**：14 个文件 + 8 个 skill 文件夹

### 心智模型数量

- researcher: 5 个
- educator: 5 个
- methodologist: 5 个
- advisor: 5 个
- **核心 4 角色合计：20 个心智模型**（每个模型 ≥2 个独立场景证据 + 局限标注，全部通过三重验证）

### 命名三件套（强约束 / 不可改）

| 字段 | 值 |
|------|-----|
| `expert_display_name` | 王受之 |
| `expert_slug` | wang-shou-zhi |
| `expert_fields` | ["设计史", "设计理论", "设计教育", "现代艺术史", "绘画", "住宅设计"] |

### Phase 2.5 决议落地确认

| 决议 | 落地位置 | 状态 |
|------|---------|------|
| **D1** · 人格戏剧张力散落实现，不显式建模为双重人格 | persona.md "表达 DNA"含"铺路石/搬运工/恰如其分"为高频术语；"价值观"第 2 条"我总是习惯看问题，不是习惯下结论"；router.md 强调"温柔姿态自然带出" | ✅ |
| **D2** · painter / real-estate-advisor 必须 ≥3 条局限 | painter/PROMPT.md 4 条局限；real-estate-advisor/PROMPT.md 4 条局限 | ✅ |
| **D3** · 应用层 skill 不重复父知识 | 4 个应用层 PROMPT.md 各自只定结构化输出模板（5 段式 / 六幕 / 4 段画家自述 / 4 步住宅区分析），心智模型引父 skill | ✅ |
| **D4** · snapshot v2 已落盘 | references/sources-index.md 引用 subject-snapshot-patched.json v2（29 条 historical_timeline）| ✅ |

### 诚实边界覆盖

- **3 大盲区已显式标注**（persona.md 诚实边界 + sources-index.md 盲区清单）：
  1. 学生 1v1 指导 / Studio Critique 现场 — 公开渠道天然零
  2. 私人通信 / 日记 / 内部讨论
  3. 72 个 B 站未转写视频（2024-2025 大量 AI 议题讲座）
- **2 个隐藏维度的 ≥3 条局限**（D2 决议）：
  - painter — 美术界无系统外部学术评价 / 无学院派油画训练 / 偏自传抒情不擅长纯形式
  - real-estate-advisor — 缺甲方/同行外部评价 / 不替代专业策划公司 / 1997-2017 黄金期方法论新周期不适用

### v0.2.0 候选迭代项（参考 `.persona-work/wang-shou-zhi/v0.2.0-iteration-candidates.md`）

| 候选项 | 优先级 | 来源 |
|-------|------|------|
| 新增 `book-writing-coach` skill — 史论 / 通识写作教练（贡布里希式）| 🟡 中 | router.md 未来扩展点 |
| 新增 `bilibili-lecture-builder` skill — B 站长视频脚本规划 | 🟡 中 | router.md 未来扩展点 |
| 新增 `cross-disciplinary-bridge` skill — 理工科学生学设计的桥接 | 🟡 中 | "我们招收的全部是理工科学生" |
| 补充 painter 的画作演化关系分析（缺策展人 / 美术史学家的连续性分析）| 🟢 低 | painter/PROMPT.md 盲区 |
| 补充 real-estate-advisor 的完整 20 年项目清单 | 🟢 低 | real-estate-advisor/PROMPT.md 盲区 |
| 补充 advisor 的应用方向（交互 / 服务 / UX）具体职业路径 | 🟢 低 | advisor/PROMPT.md 盲区 |
| 补 2026-05-12 之后新事件 | 🔴 高（一旦有新素材）| 时间锚点更新 |

### 主理人 Phase 4 关注点

- ✅ 命名三件套 expert_slug = `wang-shou-zhi`，全文一致使用
- ✅ 8 个 skill 全部为"文件夹 + PROMPT.md"标准 skill 形态（v1.0.0 强约束）
- ✅ 每个子 PROMPT.md frontmatter `name` 字段 = `wang-shou-zhi-<role>`
- ✅ 子 PROMPT.md `persona` 字段 = `../../persona.md`（多嵌套了一层）
- ⚠️ painter 和 real-estate-advisor 的局限标注**需主理人在 Phase 4 装配时再核查**——这是 D2 决议核心，质检脚本不会专门 flag
- ⚠️ critique / storyteller / painter / real-estate-advisor 4 个应用层 skill 的 `parent_skills` 字段已声明，但 painter 父声明为 `persona`（实际是 `persona.md` 而不是 skill）—— 主理人可在 Phase 4 决定是否调整为 `persona-only` 或保持
- ⚠️ examples/demo-conversations.md 共 10 组（8 组业务 + 冷启动 + 能力元问题），覆盖核心 4 + 应用 4 各 1 组——满足"≥7 组"要求

---

## 后续版本占位

### v0.2.0 · TBD · 内容迭代

- [ ] 待定
- [ ] 待定

### v1.0.0 · TBD · 正式上线版本

- 通过真实用户验证
- 王受之本人审阅确认
