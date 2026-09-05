# references 目录说明

> 本目录是王受之专家智能体的**蒸馏溯源素材**——塞吉在生成 persona / router / 8 个 skill 时所引用的全部资料索引。
> 任何 agent 输出的内容都可以通过本目录追溯到 S 编号 + 原始素材。

## 文件清单

| 文件 | 内容 | 用途 |
|------|------|------|
| `expert-profile.md` | 八路采集（A-H）画像精华 | 塞吉蒸馏时的全景视图 |
| `sources-index.md` | 完整 S 编号映射表（继承阿特拉斯 crawl-report.md §3.1）| 任何引用都能反查回原始素材 |

## 数据规模

- **一手来源**：546 条
  - priority/ 9 篇视频 ASR（S001-S009）
  - peer_reviews/ 8 篇深访（S515-S522）
  - wechat 458+14 篇（S010-S481）
  - blog 21 篇新补正文（S494-S514）+ 8 篇原（S486-S493）
  - SN001-SN006（2026-04 / 2026-03 / 2020 / 2018 增量）
- **二手来源**：18 章 books（S523-S540）—— 仅供事实校准

## 调研截止时间

**2026-05-12**

任何在 2026-05-12 之后发生的事件，agent 应承认"截至 2026-05-12 尚无更晚公开资料可查"。

## 上游团队

- **阿特拉斯**：原始素材爬取与 S 编号编制（`crawl-report.md` § 3.1）
- **艾瑞丝**：6 份结构化解析文件（`/Users/hongyu.shi/CodeBuddy/shouzhi_new/.persona-work/wang-shou-zhi/research/00-06.md`）
- **塞吉**：8 个 Skill + persona + router 蒸馏

## 重要纪律

- **ASR 名字误识清洗**：王寿芝 / 王寿森 / 王寿之 / 王秀文 等一律按"王受之"
- **风格 DNA 主力源**：priority/ + wechat 自媒体；**严禁用 books/、peer_reviews/ 提问段**
- **外部评价主力源**：peer_reviews/ + SN005/SN006 第三方语；**禁用 priority/ wechat_self（这是自评）**
- **事实层权威**：`subject-snapshot-patched.json` v2 (2026-05-13) —— 含 29 条 historical_timeline
