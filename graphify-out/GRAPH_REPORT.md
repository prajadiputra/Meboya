# Graph Report - /tmp/meboya-git  (2026-08-05)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 31 nodes · 49 edges · 9 communities (4 shown, 5 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ee293bf2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- __init__.py
- test_trace_hats.py
- _Ctx
- _format_show_hide
- _socratic_injection
- test_socratic.py
- _on_pre_llm_call
- _on_post_llm_call
- pre-commit.sh

## God Nodes (most connected - your core abstractions)
1. `register()` - 7 edges
2. `_on_post_llm_call()` - 6 edges
3. `_on_pre_llm_call()` - 5 edges
4. `_Ctx` - 5 edges
5. `_socratic_injection()` - 4 edges
6. `_format_show_hide()` - 4 edges
7. `_on_transform_llm_output()` - 4 edges
8. `reason_deeper()` - 4 edges
9. `_cmd()` - 4 edges
10. `_detect_complexity()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `register()` --indirect_call--> `_on_pre_llm_call()`  [INFERRED]
  __init__.py → __init__.py  _Bridges community 6 → community 1_
- `register()` --indirect_call--> `_on_post_llm_call()`  [INFERRED]
  __init__.py → __init__.py  _Bridges community 7 → community 1_
- `register()` --indirect_call--> `_on_transform_llm_output()`  [INFERRED]
  __init__.py → __init__.py  _Bridges community 3 → community 1_
- `register()` --indirect_call--> `_cmd()`  [INFERRED]
  __init__.py → __init__.py  _Bridges community 0 → community 1_
- `_on_post_llm_call()` --calls--> `_detect_complexity()`  [EXTRACTED]
  __init__.py → __init__.py  _Bridges community 6 → community 7_

## Import Cycles
- None detected.

## Communities (9 total, 5 thin omitted)

### Community 0 - "__init__.py"
Cohesion: 0.50
Nodes (4): _cmd(), Meboya — questioning everything. Thinking layer for Hermes Agent., _recall(), _State

### Community 1 - "test_trace_hats.py"
Cohesion: 0.60
Nodes (4): monte_carlo_simulate(), reason_deeper(), register(), Meboya trace hats regression test. Run BEFORE every commit to verify [WHITE]...[

### Community 3 - "_format_show_hide"
Cohesion: 0.50
Nodes (4): _format_show_hide(), _on_transform_llm_output(), DOGA-style: strip thinking panel when hide; keep [DECISION] + follow-up.      Pr, DOGA-style: strip <world_model> when hide; reasoning stays intact upstream.

### Community 4 - "_socratic_injection"
Cohesion: 0.67
Nodes (3): Read a core question file; return '' if missing/failed., _socratic_injection(), _socratic_read()

## Knowledge Gaps
- **2 isolated node(s):** `_State`, `pre-commit.sh script`
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `_Ctx` connect `_Ctx` to `test_trace_hats.py`?**
  _High betweenness centrality (0.207) - this node is a cross-community bridge._
- **Why does `_format_show_hide()` connect `_format_show_hide` to `__init__.py`, `test_trace_hats.py`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `_on_transform_llm_output()` connect `_format_show_hide` to `__init__.py`, `test_trace_hats.py`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `register()` (e.g. with `_cmd()` and `_on_post_llm_call()`) actually correct?**
  _`register()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `_State`, `pre-commit.sh script` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._