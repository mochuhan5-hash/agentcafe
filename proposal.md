# AgentCafe World Cafe Optimization Proposal

## 0. 当前目标

本 proposal 用于对齐 AgentCafe / LangGraph 世界咖啡多 agent 编排的下一轮优化策略。当前不直接执行代码优化，先明确：

- 世界咖啡机制中哪些行动会促进群体产生新的设计机会。
- 这些行动如何迁移到 agent 编排中的上下文管理、状态结构和系统提示词。
- 在现有 `facilitator -> table_discussion -> host_synthesis -> rotate_agents -> global_harvest` 架构上，应优先修改哪些部分。

核心原则：

> agent 优化同时包括 prompt 优化和上下文管理优化。问题设置属于 facilitator 的 prompt 层优化；问题一旦生成，又会成为后续小桌讨论的关键上下文入口。

---

## 1. 研究与机制理解

### 1.1 World Cafe 的关键机制

World Cafe 的价值不只是多人讨论，而是让多个小型、亲密、局部的对话通过轮换机制连接成一个 larger connected conversation。真正产生设计机会的动作包括：

- 用重要问题启动对话，而不是用解决方案启动对话。
- 让问题能够 travel well，在桌与桌之间流动、被重新解释、被不同经验激活。
- 通过换桌让局部洞见进入新语境，形成交叉授粉。
- 让 table host 维护本桌记忆，同时保持中立，避免成为意见领袖。
- 在 harvest 阶段让跨桌模式、稀有洞见、张力和更深问题显性化。

### 1.2 对 agent 编排的启发

对多 agent 系统来说，World Cafe 不是简单的多轮群聊，而是一个上下文流动系统：

- `facilitator` 负责把原始设计材料转化为可讨论的问题条件。
- `table host` 负责维护局部记忆，不是普通总结器。
- `speaking agent` 负责从自身视角参与讨论，并携带轻量洞见进入下一桌。
- `global harvest` 负责跨桌聚类、连接、张力识别和机会生成。

因此，优化重点应从“提高每次发言质量”转向“设计上下文如何被选择、压缩、迁移和重新激活”。

---

## 2. 优化层次划分

### 2.1 Prompt 层优化

Prompt 层优化关注的是：每类 agent 被如何定义角色、被要求执行什么动作、使用什么判断标准、避免什么偏差。

在本项目中，prompt 层优化包括：

- facilitator 如何根据用户上传文件生成高质量 table question。
- table host 如何作为中立记忆维护者、过程促进者和局部模式识别者。
- speaking agent 如何带着 pocket 进入新桌，并连接上一桌与当前桌的差异。
- global harvest 如何区分共现模式和稀有洞见。

其中，**table question 设置属于 facilitator prompt 层优化**。它的重点不是让 facilitator 替用户解决设计问题，而是通过提示词约束 facilitator：

- 先理解设计上下文中的用户需求、痛点、设计张力、少数信号和问题重构方向。
- 再生成一组互补、开放、有证据支撑、可 travel well 的小桌问题。
- 避免泛泛头脑风暴、功能模块拆分和过早解决方案。

### 2.2 上下文管理优化

上下文管理优化关注的是：什么信息被谁看到、以什么结构保存、在轮次之间如何压缩、迁移和重新激活。

在本项目中，上下文管理优化包括：

- 用户上传文件如何进入每张桌子的讨论上下文。
- table host 每轮保留哪些结构化记忆。
- speaking agent 轮换时携带什么 pocket，而不是携带完整上桌上下文。
- rotate_agents 如何路由 agent 与 pocket。
- global harvest 如何读取多桌结构化记忆，并执行双通道分析。

---

## 3. 总体上下文边界

### 3.1 用户上传文件作为共享讨论依据

用户上传文件可能包含：

- 设计背景
- 设计问题
- 目标用户画像
- 设计目标与约束
- 用户访谈记录或访谈摘要

优化后，用户上传文件仍应作为每张桌子的讨论依据提供给 table host 和 speaking agents。facilitator 的任务不是用结构化摘要替代原文，而是基于原文生成高质量 table question 设置。

需要管理的是：

- 原文可以给每桌看，但应配合本桌问题、讨论透镜和本轮子问题一起进入 prompt。
- speaking agent 轮换时不携带上一桌完整原文或完整讨论记录，只携带 pocket。
- table host 每轮压缩的是讨论产物，不是压缩用户原始文件。
- global harvest 主要读取多桌结构化记忆；如需回看原文，应作为证据校准，而不是重新做全文总结。

### 3.2 建议的上下文对象

#### 3.2.1 `source_context`

用户上传文件原文。作为每张桌子的共享讨论依据。

内容：

- 用户上传原文
- 用户输入的任务说明
- 原始访谈记录
- 原始约束和背景

使用规则：

- facilitator 用它生成 table question 设置。
- table host 和 speaking agent 可以读取它，以保证讨论有证据支撑。
- 轮换时不把某桌的完整讨论上下文带走。
- 如果原文过长，可以做技术性截断或检索，但不能用 facilitator 的结构化摘要完全替代原文。

#### 3.2.2 `table_question_plan`

由 facilitator 生成，属于 prompt 层优化的产物，也是后续 table discussion 的上下文入口。

建议结构：

```json
{
  "context_reading": {
    "user_needs": [],
    "pain_points": [],
    "design_tensions": [],
    "weak_signals": [],
    "reframe_directions": []
  },
  "tables": [
    {
      "table_id": "table_01",
      "expert_skill": "lou-yongqi / wang-meng / liu-long / wang-shouzhi / mixed",
      "expert_rationale": "为什么这个专家视角适合生成本桌问题",
      "lens": "user_journey / stakeholder_tension / root_cause / edge_case / future_scenario / reframing",
      "guiding_question": "...",
      "why_this_matters": "...",
      "evidence_basis": ["原文中的依据或证据线索"],
      "avoid_solution_bias": "...",
      "round_subquestions": {
        "round_1": ["发散观察..."],
        "round_2": ["连接与张力..."],
        "round_3": ["问题重构..."]
      }
    }
  ]
}
```

注意：这里的 `context_reading` 是为了证明 facilitator 确实读懂了上下文，并支撑问题设置；它不是给其他 agent 替代原文的摘要。

#### 3.2.3 `table_specs`

facilitator 不只生成 table question，而是生成每张桌子的讨论设计。

建议结构：

```json
{
  "table_id": "table_01",
  "expert_skill": "lou-yongqi / wang-meng / liu-long / wang-shouzhi / mixed",
  "expert_rationale": "为什么这个专家视角适合生成本桌问题",
  "lens": "user_journey / stakeholder_tension / root_cause / edge_case / future_scenario / reframing",
  "guiding_question": "...",
  "why_this_matters": "...",
  "evidence_basis": ["E1", "E4"],
  "avoid_solution_bias": "...",
  "round_subquestions": {
    "round_1": ["..."],
    "round_2": ["..."],
    "round_3": ["..."]
  }
}
```

`table_specs` 应替代当前只有 `table_questions` 的结构。

#### 3.2.4 `table_memory`

由 table host 每轮维护。它不是会议纪要，而是 table host 的 table-level intrinsic memory：随着轮次增加，host 应动态更新对本桌问题的多维度理解，观察不同轮次、不同参与者组合、不同讨论 lens 下 pattern 如何变化。

`table_memory` 与 `carry_over_packet` 的区别：

- `table_memory` 是桌子的集体内在记忆，由 table host 维护，服务于本桌连续讨论。
- `carry_over_packet` 是移动 agent 的个人迁移记忆，由 speaking agent 生成或参与生成，服务于跨桌连接。

参考 LLM-generated template 策略，`table_memory` 也不应被过细手工字段锁死。系统只保留固定外壳和更新原则；具体记忆维度由 table host LLM 根据本桌问题、source_context、上一轮 memory、本轮讨论动态生成。

建议结构采用“固定外壳 + 动态 host memory”的形式：

```json
{
  "table_id": "table_01",
  "round": 2,
  "guiding_question": "...",
  "source_context_anchor": ["本桌讨论用到的原文证据线索"],
  "host_memory_update_instruction": "LLM 为本桌 host 生成的记忆更新说明：本轮应关注哪些变化、哪些张力、哪些少数观点和哪些未完成问题。",
  "llm_generated_table_memory_template": {
    "template_name": "...",
    "fields": {
      "由 LLM 根据本桌问题和讨论情境动态生成": "..."
    }
  },
  "host_generated_table_memory": {
    "由 table host 按动态模板填入": "..."
  },
  "round_pattern_delta": "本轮相对上一轮的 pattern 变化、张力变化或问题理解变化。",
  "next_round_question_seeds": ["下一轮可引入的子问题或追问"]
}
```

保留原则仍然存在，但作为更新原则，而不是固定字段：

- 重复出现的主题必须保留，因为代表跨参与者共振。
- 少数但有启发的观点必须保留，因为可能成为创新机会。
- 未解决张力必须保留，因为问题重构通常来自张力。
- 冗余解释、礼貌性话语、低价值重复应删除或归档。
- host 应追踪轮次之间的变化，而不仅是压缩当前轮内容。

#### 3.2.5 `carry_over_packet`

每个 speaking agent 轮换时携带的轻量迁移包。它不同于 `table_memory`：

- `table_memory` 是 table-level collective memory，记录一桌集体交流过程中和结束后形成的 pattern、少数观点、未解决张力和开放问题。
- `carry_over_packet` 是 agent-level migrant memory，记录某个 agent 在与他人交流完成后形成的个人洞见，以及它准备带到下一桌测试的连接。

参考 Intrinsic Memory Agents 的 LLM-generated template 思路，`carry_over_packet` 不应追求完整保留上一桌历史，也不应依赖过细的手工字段模板。更合适的做法是：系统只提供最小路由外壳和记忆更新原则；每个 speaking agent 根据自己的角色、上一桌讨论和下一桌任务，由 LLM 动态生成适合自己的个人迁移记忆模板。

需要注意：World Cafe 不是单一任务场景。参与者每轮进入的新桌都有 facilitator 设置的不同讨论任务，因此这里的任务锚点应来自**当前桌 `table_spec`**，而不是固定不变的全局初始任务。

1. 当前桌任务描述：保持本桌目标一致性，避免 agent 把上一桌议题强行带入新桌。
2. agent 的结构化记忆：保持角色一致性，让 agent 带着自己的视角、关切和上一桌个人收获移动。
3. 最近对话转向：保持即时语境，让 agent 知道上一桌最后真正转向了什么问题。

建议结构采用“固定外壳 + 动态记忆”的形式：

```json
{
  "agent_id": "agent_01",
  "from_table": "table_01",
  "to_table": "table_02",
  "after_round": 1,
  "current_table_task_anchor": {
    "to_table_guiding_question": "...",
    "to_table_lens": "...",
    "round_subquestion": "..."
  },
  "memory_update_instruction": "LLM 为该 agent 生成的个人记忆更新说明，说明它本轮应该优先记住什么、忽略什么、如何带到下一桌。",
  "llm_generated_memory_template": {
    "template_name": "...",
    "fields": {
      "由 LLM 根据 agent 角色和讨论情境动态生成": "..."
    }
  },
  "agent_generated_memory": {
    "由 speaking agent 按动态模板填入": "..."
  },
  "bridge_intent": "一句自然语言：这个 agent 准备如何把上一桌个人洞见带到当前桌任务中测试。"
}
```

原则：

- agent 不携带完整上桌上下文。
- agent 不机械转述上一桌。
- agent 进入新桌后，应寻找上一桌洞见与当前桌讨论之间的差异、连接和新机会。
- packet 的外壳可以固定，便于系统路由；但内部记忆模板不应写死为一组手工字段。
- `memory_update_instruction` 和 `llm_generated_memory_template` 应由 LLM 根据 agent profile、上一桌讨论、当前桌 table_spec 动态生成。
- `agent_generated_memory` 由 speaking agent 根据动态模板和自己的交流体验生成，保留个人洞见，而不是复制 table_memory。

---

## 4. 各角色优化策略

## 4.1 Facilitator Agent

### 当前角色

设计每张小桌的初始讨论问题，不直接解决设计问题。

### 优化目标

facilitator 的任务是塑造能促进多 agent 高质量对话的讨论条件。

它需要：

- 将设计上下文提炼为用户需求、痛点、设计张力、少数信号和问题重构方向。
- 先判断本次设计任务适合调用哪些项目内专家 skill。
- 生成互补的 World Cafe 小桌讨论问题。
- 为每张桌子选择专家视角与讨论透镜。
- 为每轮生成子问题方向。
- 给每个问题附上证据支撑，并让后续小桌可以回到用户上传原文中讨论。

### 专家 Skill 路由

facilitator 不应只作为普通通用 agent 生成问题。用户输入问题和任务文件后，facilitator 应先做 expert-skill routing：判断哪些专家 skill 最适合参与 table question 配置，然后用这些专家知识生成更有质量的问题组合。

可用专家 skill：

| Skill | 擅长方向 | 适合生成的问题类型 |
| --- | --- | --- |
| `lou-yongqi` | 设计驱动创新、社会创新与可持续设计、服务与系统设计、城乡交互设计、设计教育 | 系统转型、社会创新、服务生态、城乡/社区、多利益相关者协作、长期可持续价值 |
| `wang-meng` | 设计+AI、知识增强大模型、多模态知识图谱、智能交互、产学研合作 | AI 介入设计流程、知识组织、人机协作、智能交互、技术系统与设计研究转译 |
| `liu-long` | 人因工程、包容性设计、用户研究、医疗器械可用性、自动驾驶信任、共创设计 | 用户旅程、可用性风险、边缘用户、包容性/老龄化、人机信任、研究验证与共创过程 |
| `wang-shouzhi` | 设计史、设计理论、设计教育、现代艺术史、住宅设计、文脉批评 | 历史脉络、设计价值判断、形式与社会语境、教育/学科批评、城市/住宅文脉 |

路由策略：

- 如果任务涉及社会创新、社区、可持续、服务系统、城乡议题，优先调用 `lou-yongqi`。
- 如果任务涉及 AI、LLM、知识图谱、智能交互、设计工具或技术系统，优先调用 `wang-meng`。
- 如果任务涉及用户研究、人因、包容性、医疗、老龄化、可用性、安全、信任，优先调用 `liu-long`。
- 如果任务涉及设计史、风格、文脉、教育、住宅、审美价值或理论判断，优先调用 `wang-shouzhi`。
- 如果任务复杂，可多 skill 协同；四桌默认可以由四个专家 skill 分别提出一张桌的问题配置，再由 facilitator 做整体去重、互补和 World Cafe 质量校准。
- 专家 skill 不是直接解决设计问题，而是帮助 facilitator 生成更好的小桌问题设置。

### 问题生成标准

每个小桌问题必须：

- 有证据支撑。
- 开放式。
- 具有生成性。
- 不带诱导性。
- 能 travel well，适合跨桌迁移和交叉授粉。
- 不按功能模块机械拆分。
- 不过早提出解决方案。

优先讨论透镜：

- 用户旅程
- 利益相关者张力
- 根因机制
- 边缘案例
- 未来场景
- 问题重构

这些透镜仍然保留，但它们作为问题质量校准框架；优先级低于 expert-skill routing。也就是说，先判断哪些专家视角能提升问题质量，再用透镜检查问题是否互补、开放、可迁移。

### Prompt 草案

```text
你是 World Cafe 多 agent 系统中的 facilitator agent。
你不是解决设计问题的人，也不是方案生成器。
你的任务是阅读用户提供的设计上下文，并把它转化为高质量的小桌讨论条件。

用户上传文件会作为后续小桌讨论的共享依据。
你的任务不是用摘要替代原文，而是基于原文设计好的 table question 设置。

在生成 table question 前，你必须先进行 expert-skill routing。
可用专家 skill：
- lou-yongqi：社会创新、可持续、服务系统、城乡交互、设计教育。
- wang-meng：设计+AI、KG/LLM、多模态知识图谱、智能交互、技术系统。
- liu-long：人因工程、包容性设计、用户研究、医疗可用性、人机信任、共创。
- wang-shouzhi：设计史、设计理论、设计教育、现代艺术史、住宅与文脉批评。

请判断本任务应调用哪些 skill 来生成桌问题配置。
如果是四桌设置，优先考虑让四个专家 skill 各自贡献一个互补的问题配置，再由你整合、去重和校准。
专家 skill 只能帮助生成问题条件，不能直接生成解决方案。

请先提炼：
- 用户需求
- 痛点
- 设计张力
- 少数但可能重要的信号
- 可能的问题重构方向

然后生成指定数量的小桌讨论设计。

每张桌子必须包含：
- lens
- expert_skill
- expert_rationale
- guiding_question
- why_this_matters
- evidence_basis
- avoid_solution_bias
- round_subquestions

问题必须开放、非诱导、有生成性，并能在不同小桌之间 travel well。
不要按功能模块拆题。
不要提出解决方案。
只输出严格 JSON。
```

---

## 4.2 Table Host Agent

### 当前问题

table host 不能只是 conversation summarizer。普通总结会丢失差异、少数观点、张力和未完成问题。

### 优化目标

table host 应是：

> 中立记忆维护者 + 过程促进者 + 局部模式识别者

### 每轮结束时保留什么

| 内容类型 | 是否保留 | 原因 |
| --- | --- | --- |
| 重复出现的主题 | 保留 | 代表跨参与者共振 |
| 少数但有启发的观点 | 必须保留 | 可能成为创新机会 |
| 未解决张力 | 必须保留 | 问题重构通常来自张力 |
| 冗余解释 | 删除 | 降低上下文噪声 |
| 礼貌性话语 | 删除 | 不贡献设计洞察 |
| 已被反复否定的低价值点 | 弱保留或归档 | 防止占用上下文窗口 |

### 每轮开始时做什么

host 需要给新进入的参与者做 1 到 3 分钟的中立 opening：

- 简洁介绍本桌 guiding_question。
- 说明上一轮形成的核心主题。
- 说明尚未解决的张力。
- 提醒本轮子问题侧重点。
- 不把上一轮结论包装成共识。
- 不引导大家接受某个方案。

此外，host 应在每轮开始前基于上一轮 `table_memory` 动态生成本轮子问题。三轮的侧重点可以作为高层 scaffold，而不是固定问题模板：

| Round | 子问题侧重点 | 生成方式 |
| --- | --- | --- |
| Round 1 | 发散观察 | 基于 `table_spec`、source_context 和本桌 lens，引导参与者打开观察面 |
| Round 2 | 连接与张力 | 基于 Round 1 的 `table_memory`，追问重复主题、少数观点和利益相关者/机制张力 |
| Round 3 | 问题重构 | 基于前两轮 pattern delta，推动参与者重构问题、提出更深问题和机会假设 |

这些子问题应由 table host 使用 LLM-generated template 策略生成：系统给出轮次目标和更新原则，具体追问维度由 LLM 根据本桌记忆动态决定。

### Prompt 草案

```text
你是 World Cafe table host agent。
你不是发言者，也不是普通 summarizer。
你的角色是：中立记忆维护者 + 过程促进者 + 局部模式识别者。

你必须：
1. 保持中立，不评价谁对谁错。
2. 记录重复主题、少数但有启发的观点、未解决张力和潜在问题重构。
3. 删除礼貌话语、冗余解释和低价值重复。
4. 当讨论停滞时，用非诱导性例子或澄清问题维持讨论。
5. 当讨论偏题时，温和拉回 guiding_question。
6. 每轮开始前，基于上一轮 table_memory 动态生成本轮子问题。
7. 每轮结束后，使用 LLM-generated template 更新 table_memory。

你的记忆不是会议纪要，而是下一轮继续生成洞察的上下文土壤。
不要把 table_memory 固定成僵硬字段表。你需要根据本桌问题、source_context、上一轮记忆和本轮讨论，动态决定本轮最值得保留的记忆维度。
```

---

## 4.3 Speaking Agent / Rotating Participant Agent

### 当前问题

如果 speaking agent 在新桌只根据新 table question 发言，World Cafe 的 larger connected conversation 会变弱。

如果 speaking agent 携带完整上桌上下文，又会造成上下文过载和机械转述。

### 优化目标

speaking agent 以“携带个人洞见”的方式进入新上下文。

它只携带一个轻量 `carry_over_packet`，而不是上一桌完整 transcript。这个 packet 不使用固定手工记忆字段，而采用 LLM-generated template：

- 系统固定提供 `current_table_task_anchor`，让 agent 围绕当前桌任务发言。
- LLM 先生成 `memory_update_instruction`，说明这个 agent 本轮应该如何更新个人迁移记忆。
- LLM 再生成 `llm_generated_memory_template`，模板字段可随 agent 角色和讨论情境变化。
- speaking agent 根据动态模板生成 `agent_generated_memory` 和 `bridge_intent`。

### 新桌发言规则

speaking agent 在新桌发言时必须区分：

- 什么来自上一桌。
- 什么来自当前桌。
- 二者之间的差异、张力或连接。

推荐发言动作：

> 上一桌的 X 与本桌的 Y 之间，可能暴露出一个新的设计机会 Z。

但这不应变成机械句式。agent 应自然地比较、连接和试探。

### Prompt 草案

```text
你是 World Cafe 轮换参与者。
你不需要复述上一桌完整内容，也不要主导新桌。
你只携带一个轻量 carry_over_packet。

这个 packet 不是上一桌总结，而是你的 agent-level migrant memory。
它包含：
- current_table_task_anchor：帮助你围绕当前桌任务发言。
- memory_update_instruction：告诉你本轮应该如何更新自己的个人迁移记忆。
- llm_generated_memory_template：根据你的角色、上一桌经历和当前桌任务动态生成，不是手工固定模板。
- agent_generated_memory：你根据动态模板形成的个人洞见。
- bridge_intent：你准备如何把上一桌个人洞见带到当前桌测试。

发言时请区分：
- 来自上一桌的洞见
- 当前桌正在形成的观点
- 二者之间的差异、张力或新连接

请优先寻找：
上一桌的 X 与本桌的 Y 之间，是否存在新的设计机会、问题重构或需要验证的假设。

不要把上一桌观点强行灌入新桌。
不要过早提出完整方案。
请控制在 300 字以内。
```

---

## 4.4 Global Harvest Agent

### 当前问题

普通 summary merger 会偏向高频内容，容易吞掉低频但重要的弱信号。

### 优化目标

global harvest agent 不只是合并多桌摘要，而是做四件事：

- 聚类
- 连接
- 张力识别
- 机会生成

### 双通道分析

| 通道 | 关注内容 | 作用 |
| --- | --- | --- |
| Pattern Channel | 多桌重复出现的主题 | 识别集体共识、主要问题和系统性模式 |
| Weak Signal Channel | 只出现一次但有启发的观点 | 发现少数意见、新概念和潜在创新机会 |

### 输出结构

```json
{
  "cross_table_patterns": [
    {
      "pattern": "...",
      "seen_in_tables": ["table_01", "table_03"],
      "why_it_matters": "..."
    }
  ],
  "rare_but_promising_signals": [
    {
      "signal": "...",
      "from_table": "table_02",
      "why_it_matters": "...",
      "risk_if_ignored": "..."
    }
  ],
  "unresolved_system_tensions": [
    {
      "tension": "...",
      "tables_involved": ["table_01", "table_04"],
      "possible_reframe": "..."
    }
  ],
  "opportunity_hypotheses": [
    {
      "hypothesis": "...",
      "based_on": ["pattern_or_signal_id"],
      "next_learning_action": "..."
    }
  ],
  "reframed_design_questions": [
    "..."
  ],
  "next_learning_experiments": [
    {
      "experiment": "...",
      "what_to_observe": "...",
      "why_now": "..."
    }
  ]
}
```

### Prompt 草案

```text
你是 World Cafe global harvest agent。
你不是普通摘要合并器。
你要做四件事：聚类、连接、张力识别、机会生成。

请使用双通道分析：
1. Pattern Channel：识别多桌重复出现的主题、共识和系统性问题。
2. Weak Signal Channel：识别只出现一次但高张力、高新颖、高启发的少数观点。

不要只按频率排序。
不要抹平分歧。
不要直接生成完整设计方案。
请输出可继续研究、验证和重构问题的 harvest。
```

---

## 5. 建议的 LangGraph 流程改造

当前流程：

```text
setup
-> begin_round
-> table_discussion
-> collect_round
-> rotate_agents
-> global_harvest
```

建议流程：

```text
facilitate_context
-> setup
-> begin_round
-> host_opening
-> table_discussion
-> host_synthesis
-> pocket_generation
-> collect_round
-> rotate_agents
-> global_harvest
```

### 节点说明

#### `facilitate_context`

- 输入 user request + source_context。
- 输出 `table_question_plan` 和 `table_specs`。
- source_context 继续作为每张桌子的共享讨论依据进入后续 table discussion。

#### `host_opening`

- 每桌每轮开始时运行。
- 输入本桌 `table_spec`、source_context、上一轮 `table_memory`、round focus。
- 使用 LLM-generated template 生成本轮 `next_round_question_seeds`。
- 输出简短 opening，用于新参与者快速进入讨论。
- 本轮问题侧重点：
  - Round 1: 发散观察
  - Round 2: 连接与张力
  - Round 3: 问题重构

#### `table_discussion`

- 输入：
  - 本桌 `table_spec`
  - 用户上传文件 `source_context`
  - 当前 `table_memory`
  - 当前轮 conversation
  - agent profile
  - agent carry_over_packet
- speaking agent 不接收上一桌完整讨论上下文，只接收自己的 carry_over_packet。

#### `host_synthesis`

- 输入本轮发言、本桌上一轮 memory、本轮 question focus、source_context。
- 第一阶段：生成或更新 `host_memory_update_instruction` 和 `llm_generated_table_memory_template`。
- 第二阶段：table host 根据动态模板生成 `host_generated_table_memory`、`round_pattern_delta` 和下一轮 `question_seeds`。
- 输出 table-level intrinsic memory JSON。

#### `pocket_generation`

- 为每个将要轮换的 speaking agent 生成 agent-level `carry_over_packet`。
- packet 不是 `table_memory` 的复制，也不是上一桌完整摘要，而是面向下一桌的个人迁移记忆。
- packet 来源于：
  - 本桌 table_memory
  - agent 本轮自己的贡献
  - 本桌最近的对话转向
  - 本桌 unresolved tensions / minority views
  - agent profile
  - 下一桌 table_spec
- packet 生成采用 LLM-generated template，两阶段完成：
  - 第一阶段：根据 agent profile、上一桌讨论、上一桌 table_memory、下一桌 table_spec，生成 `memory_update_instruction` 和 `llm_generated_memory_template`。
  - 第二阶段：speaking agent 根据这个动态模板生成 `agent_generated_memory` 和 `bridge_intent`。
- 固定字段只保留系统路由和当前桌任务锚点：
  - `agent_id`
  - `from_table`
  - `to_table`
  - `after_round`
  - `current_table_task_anchor`

#### `rotate_agents`

- 保留现有“桌长不轮换，speaking agents 顺时针轮换”的机制。
- 新增：将生成好的 packet 绑定到 agent 下一轮所在桌。
- `rotate_agents` 只负责路由 agent 与 packet，不负责生成或解释 packet。

#### `global_harvest`

- 输入所有桌子的最终 `table_memory`、round history、carry-over trace。
- 输出双通道 harvest。

---

## 6. 状态结构修改建议

当前 `WorldCafeState` 中已有：

- `background_context`
- `table_questions`
- `table_memories`
- `round_summaries`
- `rotation_history`
- `harvest`

建议新增或替换：

```python
source_context: str
table_question_plan: dict[str, Any]
table_specs: dict[str, TableSpec]
expert_skill_routes: dict[str, Any]  # facilitator routing decisions for lou-yongqi / wang-meng / liu-long / wang-shouzhi
table_memory_templates: dict[str, Any]  # host LLM-generated memory templates by table/round
agent_pockets: dict[str, CarryOverPacket]  # route shell + LLM-generated memory template + agent-generated memory
pocket_history: list[dict[str, Any]]
host_openings: list[dict[str, Any]]
question_seed_history: list[dict[str, Any]]
```

建议逐步弃用：

```python
background_context -> source_context，作为每桌共享讨论依据
table_questions -> table_specs[table_id]["guiding_question"]
round_summaries -> 可保留，但从普通摘要改为结构化 round records
```

---

## 7. Prompt 与解析策略

### 7.1 优先使用严格 JSON

建议 facilitator、host_synthesis、pocket_generation、global_harvest 都输出 JSON。

原因：

- 当前 Markdown section parsing 容易受标题变体影响。
- 结构化 JSON 更适合跨节点传递。
- 可以更容易写测试，确保字段存在、长度可控、问题设置有依据。

### 7.2 speaking agent 仍可输出自然语言

speaking agent 的贡献可以继续是自然语言，因为讨论本身需要开放性。

但 prompt 应明确：

- 不要机械总结。
- 不要直接给方案。
- 不要复述完整 pocket。
- 尝试连接上一桌和本桌的差异。

---

## 8. 实施优先级

### Phase 1: Facilitator 问题设置 prompt 优化

- 重写 facilitator prompt。
- 明确 facilitator 不直接解决设计问题，只设计小桌初始问题。
- 新增 expert-skill routing：根据用户任务和上传文件判断应调用 `lou-yongqi`、`wang-meng`、`liu-long`、`wang-shouzhi` 中的哪些专家视角。
- 四桌默认可让四个专家 skill 各自贡献一个问题配置，再由 facilitator 做 World Cafe 质量校准。
- 要求 facilitator 提炼用户需求、痛点、设计张力、少数信号和问题重构方向。
- 要求每个 table question 有证据支撑、开放、生成性、不诱导、能交叉授粉。
- 要求使用用户旅程、利益相关者张力、根因机制、边缘案例、未来场景、问题重构等透镜做二次校准。

### Phase 2: Facilitator 输出升级

- 将 facilitator 输出从 `tables: [{table_id, question}]` 升级为 `table_question_plan + table_specs`。
- `table_specs` 增加 `expert_skill` 和 `expert_rationale`。
- 保持前端兼容：仍可从 `table_specs.guiding_question` 渲染问题。
- 保持用户上传文件作为每张桌子的共享讨论依据。

### Phase 3: Table Host 内在记忆与动态子问题

- 扩展 `TableMemory`。
- 重写 host prompt。
- 使用 LLM-generated template 更新 table-level intrinsic memory。
- 每轮开始前基于上一轮 table_memory 生成本轮 question seeds。
- Round 1 / 2 / 3 分别偏向发散观察、连接与张力、问题重构。
- collect 阶段改为合并动态 memory、pattern delta 和 question seeds。

### Phase 4: Carry-over Packet

- 新增 pocket generation。
- rotation 时绑定 `from_table -> to_table`。
- participant prompt 接收自己的 packet。

### Phase 5: Global Harvest 双通道

- 重写 global harvest prompt。
- 输出 pattern channel + weak signal channel。
- 前端 harvest 展示可先渲染 JSON 转 Markdown，也可后续单独优化。

---

## 9. 需要我们对齐的问题

1. 用户上传文件原文进入每桌 prompt 时，是否需要按长度做截断或检索式片段选择？
2. `table host` 是否完全不参与发言，还是允许在讨论停滞/偏题时插入过程促进语？
3. `carry_over_packet` 是由 host 生成，还是由每个 speaking agent 自己生成后再由 host 压缩校准？
4. `global_harvest` 输出应优先保持 Markdown 便于前端显示，还是改为 JSON 后再渲染？
5. 第一轮是否需要 pocket？默认应为空，还是允许 agent 携带自己的 profile-based concern？

---

## 10. 初步建议

我的建议是：

1. 用户上传文件原文继续进入每桌讨论；如果过长，先使用统一截断策略，后续再升级为检索式片段选择。
2. table host 不作为普通发言者，但允许在停滞或偏题时输出 process intervention。
3. carry-over packet 采用 speaking agent 的 LLM-generated template：系统提供路由外壳和当前桌任务锚点，speaking agent 生成个人迁移记忆；可选增加轻量校验，防止脱离上一桌讨论证据。
4. global harvest 内部输出 JSON，最终再格式化成 Markdown 给前端。
5. 第一轮 pocket 为空，但 agent 可基于 profile 和 table question 发言。

---

## 11. 下一步

我们可以先一起修改本 proposal，确定策略后再进入代码实现。

建议优先确认：

- 用户上传文件如何进入每桌 prompt，是否需要截断或检索。
- table host 是否允许中途过程干预。
- `carry_over_packet` 的生成责任归属。
- 输出格式先 JSON 还是 Markdown。
- 是否分 phase 实施，还是一次性改完。

---

## 12. 参考来源

- World Cafe 官方原则：关注重要问题、连接多样视角、共同聆听模式与洞察、harvest 集体发现。
- Löhr 等关于 World Cafe 与 focus group 差异的讨论：轮换参与者让多个小组对话连接成 larger connected conversation，并缓解 group imbalance。
- Intrinsic Memory Agents: Contextualizing LLMs for Long-Horizon Interactive Multi-Agent Simulations, arXiv:2508.08997v2。用于启发 `carry_over_packet` 的 LLM-generated template 策略：避免过细手工模板，只保留系统外壳和更新原则，让 LLM 根据 agent、任务和最近互动动态生成记忆模板。在 World Cafe 场景中，任务锚点应改写为当前桌 `table_spec`，因为参与者每轮进入的桌子任务会变化。
