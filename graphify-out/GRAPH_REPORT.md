# Graph Report - .  (2026-07-25)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 25 nodes · 41 edges · 5 communities (3 shown, 2 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- __init__.py
- register
- _Ctx
- test_trace_hats.py
- pre-commit.sh

## God Nodes (most connected - your core abstractions)
1. `register()` - 7 edges
2. `_on_post_llm_call()` - 5 edges
3. `_Ctx` - 5 edges
4. `_format_show_hide()` - 4 edges
5. `_on_pre_llm_call()` - 4 edges
6. `_on_transform_llm_output()` - 4 edges
7. `reason_deeper()` - 4 edges
8. `_cmd()` - 4 edges
9. `_detect_complexity()` - 3 edges
10. `monte_carlo_simulate()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `register()` --indirect_call--> `_on_pre_llm_call()`  [INFERRED]
  __init__.py → __init__.py  _Bridges community 0 → community 1_
- `register()` --calls--> `reason_deeper()`  [EXTRACTED]
  __init__.py → __init__.py  _Bridges community 3 → community 1_

## Import Cycles
- None detected.

## Communities (5 total, 2 thin omitted)

### Community 0 - "__init__.py"
Cohesion: 0.33
Nodes (8): _cmd(), _detect_complexity(), _on_post_llm_call(), _on_pre_llm_call(), Meboya — questioning everything. Thinking layer for Hermes Agent., _recall(), _remember(), _State

### Community 1 - "register"
Cohesion: 0.40
Nodes (5): _format_show_hide(), _on_transform_llm_output(), DOGA-style: strip <world_model> when hide; reasoning stays intact upstream., DOGA-style: strip thinking panel when hide; keep [DECISION] + follow-up.      Pr, register()

### Community 3 - "test_trace_hats.py"
Cohesion: 0.67
Nodes (3): monte_carlo_simulate(), reason_deeper(), Meboya trace hats regression test. Run BEFORE every commit to verify [WHITE]...[

## Knowledge Gaps
- **2 isolated node(s):** `_State`, `pre-commit.sh script`
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `_Ctx` connect `_Ctx` to `test_trace_hats.py`?**
  _High betweenness centrality (0.283) - this node is a cross-community bridge._
- **Why does `_format_show_hide()` connect `register` to `__init__.py`, `test_trace_hats.py`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Why does `_on_transform_llm_output()` connect `register` to `__init__.py`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `register()` (e.g. with `_cmd()` and `_on_post_llm_call()`) actually correct?**
  _`register()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `_State`, `pre-commit.sh script` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._