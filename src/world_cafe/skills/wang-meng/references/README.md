# 王萌 · 溯源素材索引

> 本目录存放王萌专家智能体的全部溯源素材（v0.2.0 版本，v1 + v2 增量合并）。

## 文件清单

| 文件 | 用途 |
|------|------|
| `README.md` | 本文档，目录导航 |
| `expert-profile.md` | 八路采集画像精华（v1 + v2 合并版） |
| `sources-index.md` | 完整素材索引（S1-S31 + L-S1-L-S4 + 已排除项 X1-X2） |
| `research/` | 艾瑞丝 v1 + v2 增量解析合并 |

## research/ 子目录结构

每个研究维度有 **2 份文件**：v1 既有版（基线，**只读不修改**）+ v2 增量 delta 版（`*.delta.md`，含 X-VAL / REVISE / NEW 三态标签）。

| 维度 | v1 基线版 | v2 增量 delta |
|------|---------|---------|
| 著作与系统性论文 | `01-writings.md` | `01-writings.delta.md`（修正位次 + NeurIPS/ICML 主题归类 + 蚂蚁链 + 王毕伦链） |
| 访谈 / 演讲 / 对话 | `02-conversations.md` | `02-conversations.delta.md` ⭐**最重要** — 含 [S28]/[S29]/[S30]/[S31] 完整解析 + 末尾**塞吉视角候选 L3 三件套** |
| 语言风格 DNA | `03-expression-dna.md` | `03-expression-dna.delta.md` — 18 高频术语 X-VAL/REVISE/NEW 重排 + 同济期 5 项新句式 + 14 项新术语 |
| 外部评价 | `04-external-views.md` | `04-external-views.delta.md` — 5 个 v1 未捕捉合作锚点（娄永琪 / 马进 / 纪丹文 / 王毕伦链 / 蚂蚁链） |
| 决策节点 | `05-decisions.md` | `05-decisions.delta.md` — 决策节点 #4/#5 月级精度补全 + NEW 决策节点 #6 同济期产品化 |
| 时间线 | `06-timeline.md` | `06-timeline.delta.md` — 同济期月级精度节点 + 东南期 2020-11 演讲节点补充 |

## v0.2.0 重构原则

1. **v1 既有 reference 只读不修改** — 保持原始 audit trail
2. **v2 增量 delta 与 v1 共存** — 共同构成「演化轨迹」
3. **shipped 给用户的 persona / skills / examples 已充分吸收 v2 增量** — 用户不需要直接读 reference 也能得到完整 v2 体验
4. **对每条修订 / 新增的诚实标注** — v2 delta 文件中每条都带 X-VAL / REVISE / NEW 三态标签 + 来源 [S 编号] + 阶段标【东南】/【同济】/【跨阶段】

## 溯源原则

1. **所有跨阶段稳定特质（L3）+ 论点（在 perspective 子 skill 中）+ 案例 + 金句**必须可追溯到 S 编号一手来源
2. **诚实边界**统一收纳在 `persona.md` 末尾（不分散到其他文件）
3. **已排除项（X1/X2）** 明确记录在 `sources-index.md`，不做引用
4. **双标注事实**（博导 + 预聘副教授 / Nature Microbiology 笔误 / 专著书名不公开 / NeurIPS+ICML 主题修正等）必须保留并行记录

## 累计可信度统计（v0.2.0）

| 级别 | v1 数量 | v2 新增 | 合计 |
|------|--------|--------|------|
| 🔴 一手 | 18 | +4（[S28] / [S29] / [S30] / [S31]）| **22** |
| 🟡 二手 | 13 | 0 | 13 |
| 🟢 三手 | 2 | 0 | 2 |
| ⛔ 已排除 | 2 | 0 | 2 |
| **可引用 S 编号合计** | 31 | +4 | **35** |
