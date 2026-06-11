# 娄永琪 · 蒸馏素材索引（References）

> 本目录汇集 `lou-yongqi/` Agent 的全部蒸馏溯源素材——阿特拉斯的原始爬取产物 + 艾瑞丝的结构化分析产物 + 蒸馏者（塞吉）的综合画像。
> 每个 skill / persona / demo 里用到的 `[Sx]` 或 `[LXn-m]` 编号都可以在本目录的 `sources-index.md` 里定位到原文。

---

## 目录结构

```
references/
├── README.md                        ← 你在这里
├── expert-profile.md                ← 八路采集画像精华（一页纸看懂娄永琪）
├── sources-index.md                 ← 完整素材索引（继承阿特拉斯的 S 编号 + 乐享 LX 编号）
├── research/                        ← 艾瑞丝 Phase 2 结构化分析产物（6 份）
│   ├── 01-writings.md               ← 学术产出、8 篇代表作、《She Ji》、DesignX、T 型、Treccani 词条
│   ├── 02-conversations.md          ← 15 主题 / 410+ 直接引语（塞吉最重要的输入）
│   ├── 03-expression-dna.md         ← 40+ 术语 / 6 句式 / 10 口癖 / 39 金句 / 10 "不会说的话"
│   ├── 04-external-views.md         ← 瑞典工程院 / RCA 颁词 / CUMULUS / 狮子骑士 / 学术网络
│   ├── 05-decisions.md              ← 5 fields × 7-11 决策节点
│   └── 06-timeline.md               ← 1974-2026 完整时间线 / 期刊编辑与国际职务总表
└── sources/                         ← 阿特拉斯 Phase 1 原始爬取素材
    ├── public-web/                  ← 公开域 S1-S16
    │   └── atlas-public-domain-report.md
    └── lexiang/                     ← 乐享 LX1-70 / LX2-20 / LX3-10
        ├── atlas-lexiang-report-v2.md
        └── content/                 ← 100 条裸正文（若需校准原话可读这里）
```

---

## 读素材的优先顺序

### 场景 A：写 skill / persona 时找 DNA 素材
1. **先读** `research/03-expression-dna.md`（语言 DNA 最稠密）
2. **再读** `research/02-conversations.md`（找直接引语，按主题聚类）
3. **必要时查** `research/01-writings.md`（学术产出的权威版本）

### 场景 B：写心智模型找证据
1. **先读** `research/05-decisions.md`（按 5 fields 已整理好决策节点）
2. **再读** `research/02-conversations.md`（找原话 + 场合）
3. **校准事实用** `research/06-timeline.md`（时间、职务、获奖年份）

### 场景 C：需要外部视角（他人评价 / 国际地位）
1. **先读** `research/04-external-views.md`（瑞典工程院 / RCA / CUMULUS / 学生昵称"娄骑士"）
2. **再读** `research/06-timeline.md`（国际职务表）

### 场景 D：追溯某条引语的具体出处
1. **先查** `sources-index.md` 找到 S/LX 编号
2. **需要原话完整语境时**读 `sources/lexiang/content/{entry_id}.md` 或 `sources/public-web/atlas-public-domain-report.md`
3. **如果是英文原话**（RCA / CHI 等）—— 现有语料多为中文转译，LX3-3 是唯一英文长文样本

---

## 编号约定

| 前缀 | 含义 | 来源 |
|---|---|---|
| **S1–S16** | 公开域来源（官网、期刊数据库、新闻媒体、政府公文、百度百科等） | 阿特拉斯 `atlas-public-domain-report.md` |
| **LX1-1 ~ LX1-70** | 乐享域文章 / 专访 / 学术论文 / 政策文件 | 阿特拉斯 `atlas-lexiang-report-v2.md` |
| **LX2-1 ~ LX2-20** | 乐享域演讲 / 讲座转写（口语化） | 同上 |
| **LX3-1 ~ LX3-10** | 乐享域本人署名长文（含中文 + 英文） | 同上 |
| **dc56d8d...** | 特殊 entry_id（造就思想节 "我办了一所中学" 完整稿，与 LX2-13 同内容不同抄本） | `sources/lexiang/content/dc56d8d129bb44728058747436dcbb32.md` |

---

## 盲区清单（蒸馏时需要带不确定性）

> 详见 `expert-profile.md` 末尾，这里列摘要：

1. **博士论文题目与导师姓名**（CNKI 付费墙）—— 盲区 #1
2. **2002–2007 建筑师生涯具体作品清单**（仅有"约 40 万平方米"概括数字）—— 盲区 #3
3. **2015–2022 间约 57 条 Space 1 文章**（乐享配额限流未拉通）—— 盲区 #4
4. **英文原话稿**（RCA / CHI / 米兰三年展中英文仅有中文转译）
5. **私下 / 家庭 / 挚友口吻**（现有语料全为公开场合发言）
6. **国际同行的批评性评价**（现有评价几乎全部正面）
7. **设计丰收财务闭环 / NICE 2035 物业纠纷细节**（本人承认存在但未展开）
8. **上工大"三旋翼"战略具体教学改革路径**（2025 在落地中，细节尚在展开）

---

## 注意事项（塞吉留给后续版本维护者）

1. **不要覆盖 `research/` 和 `sources/` 下的文件** —— 那是艾瑞丝和阿特拉斯的产物，应当保持原样
2. **新增素材按编号规则命名** —— 不要重用已有的 S/LX 编号
3. **引用时必须带编号** —— 方便下游校验（persona.md 与 skill 内所有引用都严格带 S/LX 编号）
4. **本人身份/事实类描述优先引 S1–S3（官网）+ LX1-45（澎湃任前公示）+ S9（政府公文）**
5. **语言 DNA 类引用优先引 S5 + S12/LX1-66 + LX1-13（书面学术口吻）** + LX2 系列（口语化补色）
6. **更新时同步更新 `sources-index.md` 与 `evolution-log.md`**
