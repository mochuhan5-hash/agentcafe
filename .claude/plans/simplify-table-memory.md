# Plan: 精简 TableMemory 对齐 host_synthesis_prompt 输出

## 目标

`TableMemory` 结构对齐 `host_synthesis_prompt` 的输出，移除所有冗余派生字段。

## 新 TableMemory 结构

```python
class TableMemory(TypedDict, total=False):
    table_id: str
    question: str
    host_id: str
    tablememory_usage_description: str
    formatmemory: list[dict[str, Any]]  # 按轮累计，每条含 round_index/repeated_themes/minority_inspiring_views/unresolved_tensions
    next_round_question_seeds: list[str]
```

移除字段：`living_summary`, `key_insights`, `open_questions`, `tensions`, `stable_patterns`, `incomplete_or_weak_patterns`, `contested_points`, `blind_spots_or_ambiguities`, `rounds`, `source_context_anchor`, `cumulative_pattern_evolution`, `recurring_patterns_across_rounds`, `emerging_or_fading_signals`, `unresolved_tensions_over_time`, `round_pattern_delta`

## 修改文件

### 1. `state.py` — 精简 TypedDict
删除上述多余字段。

### 2. `graph.py` — 精简 `_collect_round` 和相关函数
- `_empty_table_memory`: 只保留 `table_id`, `question`, `host_id`, `tablememory_usage_description`, `formatmemory: []`, `next_round_question_seeds: []`
- `_collect_round` (line 470-533): 只做：
  1. append formatmemory_record 到 `memory["formatmemory"]`
  2. 更新 `memory["next_round_question_seeds"]`
  3. 更新 `memory["tablememory_usage_description"]`
  - 移除所有 living_summary/key_insights/stable_patterns/etc 的赋值
- `_parse_host_memory_update` (line 1339-1405): 简化返回值，只保留 `formatmemory`, `next_round_question_seeds`, `tablememory_usage_description`（加 `synthesis` 给 closing display 用）
- `_host_memory_snapshot` (line 906-989): 简化，从 formatmemory 列表中构建 snapshot（recent_rounds 保留给 UI tooltip 用）
- `_format_host_record_display` (line 1002-): 从 formatmemory record 中读取，不再依赖 memory_update 的多余字段
- `TableRoundOutput`: 移除 `key_insights`, `open_questions`, `tensions`（这些可从 table_memory_update.formatmemory 中取）
- `host_event` emit: `key_insights`/`open_questions`/`tensions` 从 formatmemory record 中取
- `memory["rounds"]` 列表也移除（原来存了每轮的完整快照，现在 formatmemory 列表已经按轮累计）

### 3. `context.py` — 简化所有 view 函数
所有 view 只读取 `question`, `formatmemory`（列表）, `next_round_question_seeds`, `tablememory_usage_description`。  
移除对 `living_summary`, `rounds` 等字段的引用。不同 view 通过 `limit` 参数控制展示多少轮的 formatmemory。

### 4. `prompts.py` — 无需改动
`format_memory` 调用 `context.py` 的函数，prompt 本身不直接读 TableMemory 字段。

## 影响确认
- `host_synthesis_prompt` 已有 `既有 formatmemory（按轮顺序记录）` 传入 → 仍然工作
- `contribution_prompt` 用 `format_memory(memory, view='speaker')` → context.py 简化后仍可输出
- `host_opening_prompt` 同理
- `global_harvest_prompt` 已改为只用 speaking history → 不读 TableMemory 了
- UI tooltip (`_host_memory_snapshot`) 仍可从 formatmemory 列表构建 recent_rounds
