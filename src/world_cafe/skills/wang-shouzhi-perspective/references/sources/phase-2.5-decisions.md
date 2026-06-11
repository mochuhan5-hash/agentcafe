# Phase 2.5 决议固化

> 日期：2026-05-13  
> 主理人：蒸馏总协调师  
> 状态：用户已最终确认，**塞吉蒸馏全程禁止再修改本文件中的任何字段**。

## 命名三件套（强约束）

| 字段 | 值 |
|---|---|
| `expert_display_name` | **王受之** |
| `expert_slug` | **wang-shou-zhi** |
| `expert_fields` | **["设计史", "设计理论", "设计教育", "现代艺术史", "绘画", "住宅设计"]**（已扩充至 6 项，含 Q1/Q2 新维度） |
| 专家类型 | **学术型 + 公共型** 双适配 |
| 方向 Profile | **学术型 · 设计学 · 设计史/设计理论** |
| 输出根目录 | **`/Users/hongyu.shi/CodeBuddy/shouzhi_new/wang-shou-zhi/`** |
| 语言 | **中文为主，特殊学术语境保留英文**（如 Bauhaus、Art Center、Entertainment Design、Memphis） |
| 深度 | **混合**：persona 与 critique/storyteller 用实战表达 ；researcher/methodologist/educator/advisor 用学术严谨 |

## Skill 集架构（8 个子文件夹，全部必须为「文件夹+PROMPT.md」标准 skill 形态）

### 核心角色（4 个，必有）
| 子目录 | name 字段 | 重点 |
|---|---|---|
| `skills/researcher/` | `wang-shou-zhi-researcher` | 设计史研究方法 / 风格谱系 / 论文写作 |
| `skills/educator/` | `wang-shou-zhi-educator` | 设计教育批判 / Critique 模式 / 教学哲学 / 同质化反思 |
| `skills/methodologist/` | `wang-shou-zhi-methodologist` | 设计史三轴分析（风格/社会语境/技术驱动）/ AI 四维框架（技术-媒介-审美-社会）/ 史论写作工具箱 |
| `skills/advisor/` | `wang-shou-zhi-advisor` | 给学设计的年轻人做职业路径 / 阅读路线 / 留学选择建议 |

### 应用层（4 个，全部启用）
| 子目录 | name 字段 | 重点 |
|---|---|---|
| `skills/critique/` | `wang-shou-zhi-critique` | 对一件设计作品做设计史视角 5 段式评论 |
| `skills/design-history-storyteller/` | `wang-shou-zhi-design-history-storyteller` | ⭐ 把设计史讲成故事（模拟他 B 站讲课/一席演讲风格，"先讲故事再下论断"句式 + 自嘲幽默） |
| `skills/painter/` | `wang-shou-zhi-painter` | 🆕 画家身份维度，谈美感/手艺/创作冲动；外部评价缺失需在 Skill 内显式标注 ≥3 条局限 |
| `skills/real-estate-advisor/` | `wang-shou-zhi-real-estate-advisor` | 🆕 住宅区规划 / 楼盘命名 / 商业地产文脉；20 年实操 + 著作《当代商业住宅区的规划与设计》；需标注"无法替代具体地产策划公司"等局限 |

## 关键架构决定

### D1 · 人格戏剧张力（不专设节，散落实现）
艾瑞丝发现的"外部定性 vs 自我定位"不对称（"奠基人/铺路石"、"批判家/温柔姿态"），**不**在 persona.md 中独立成节，而是：
1. **散入 `persona.md` 的"表达 DNA"章节**：把"铺路石/搬运工/恰如其分"作为高频术语之一（来自艾瑞丝 03-expression-dna §1 术语 5/6）
2. **散入 `persona.md` 的"价值观与信念"章节**：把"我总是习惯看问题，不是习惯下结论" 作为信念之一
3. 蒸馏时**不要把这种张力做成显式分裂的两套人格**，而是让 agent 在回答尖锐问题时**自然带出温柔姿态**

### D2 · painter 与 real-estate-advisor 子 Skill 的局限标注（强约束）
两个新增子 Skill 因外部评价/方法论证据较薄，**必须在 PROMPT.md 中显式声明 ≥3 条具体局限**：
- `painter`：
  1. 美术界至今无系统外部评论家对其画家身份做学术定性
  2. 其绘画训练背景（汉口 18 岁做美编 + 自学）与学院派油画训练有显著差距
  3. 其画作偏自传性/抒情性，不擅长纯形式探索
- `real-estate-advisor`：
  1. 大多素材为自述 + 零散公众号回忆，缺乏甲方/同行系统评价
  2. 其住宅顾问角色偏"文脉与意象命名"，**不**替代专业地产策划公司的市场/财务模型
  3. 时代背景为 1997-2017 中国地产黄金期，其方法论在当下 2025+ 地产新周期下的适用性有限

### D3 · 不重复父 Skill 知识（v1.0.0 强约束）
四个应用层 Skill（critique / storyteller / painter / real-estate-advisor）的 PROMPT.md **不重复 researcher/educator/methodologist 的心智模型**，只定义结构化输出模板（5 段式评审 / 故事六幕脚本 / 画家自述模板 / 住宅区分析框架）。

### D4 · snapshot v2 已落盘
基于艾瑞丝 06-timeline 发现，已追加 10 条已有 S 编号印证的 historical_timeline 事件；不修改 current_snapshot 字段以避免越补越乱。详见 `subject-snapshot-patched.json` 的 `patch_history.p2-2026-05-13`。

## 塞吉的输入清单（主理人将一并传递）

1. 团队元框架 `references/distillation-framework.md`（必读 — 八路骨架/三层金字塔/专家类型适配器/Profile/三重验证/八路→文件映射/命名强约束）
2. 团队模板 `templates/` 下 7 份模板
3. 共享 Skill `expert-creator`（产物文件树规范）
4. 艾瑞丝 7 份解析文件（`.persona-work/wang-shou-zhi/research/`）
5. patched snapshot v2（事实层权威，`subject-snapshot-patched.json`）
6. 阿特拉斯 crawl-report.md（S 编号总表 + 盲区报告）
7. **本文件**（Phase 2.5 决议，命名/架构/局限标注全部硬约束）

## 不可议项（塞吉禁动）

- ❌ 不得改 expert_slug
- ❌ 不得把"绘画"或"住宅设计"翻成英文 fields
- ❌ 不得跳过 painter / real-estate-advisor 子 Skill 的 ≥3 条局限标注
- ❌ 不得把人格张力做成"双重人格"的显式分裂建模
- ❌ 不得引导用户"复制到 ~/.learningbuddy/"或"创建 .meta.json"（团队元框架第一章第 8 条）
- ❌ 不得把核心 4 角色或子 Skill 写成单文件 `skills/researcher.md`（v0.1.0 已废弃）
