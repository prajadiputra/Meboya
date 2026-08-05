# Meboya 🔍

> **Bali: *meboya* = "questioning everything"**  
> Structured reasoning plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent) — Six Thinking Hats + Critical pushback + DOGA-compatible show/hide + Monte Carlo simulation + recursive self-critique.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.7.5-green)](https://github.com/prajadiputra/Meboya/releases)

---

## Features

| Feature | Description |
|---|---|
| 🎩 **Six Thinking Hats** | [WHITE] facts → [BLACK] risks → [RED] gut → [YELLOW] benefits → [GREEN] alternatives → [BLUE] synthesis |
| 🔍 **Critical Mode** (ON by default) | Adversarial pushback with `├ CRITICAL:` sub-points on BLACK, GREEN, BLUE |
| 📊 **Decision Block** | MANDATORY [DECISION] with Decision, Key Reason, Risk Accepted, Action |
| 👁️ **Show / Hide** (DOGA-style) | Toggle trace visibility via `transform_llm_output` — reasoning continues, panel hidden |
| 🎲 **Monte Carlo Simulation** | Pure Python probability engine (1K–50K iterations, 0 LLM tokens) |
| 🔄 **Reason Deeper** (recursive self-critique) | Model can invoke `reason_deeper` tool to self-audit with hat lens |
| 🛑 **Hard-Break** | Auto-blocks `reason_deeper` after 3 ignored calls; manual on/off available |
| ⚡ **Auto-Depth** | Complexity detection per query (low/medium/high, 0 LLM tokens) |
| 🧠 **Mnemosyne Memory** (optional) | Recalls past queries, saves goal patterns across sessions |
| 🪶 **Zero Hard Dependencies** | Pure Python stdlib — Mnemosyne optional |
| ❓ **Socratic Enhancement** | Auto-injects a curated senior-engineer question bank (15 domains) when the task signals build/design/migrate/review work |

---

## Socratic Enhancement 🧠

**Auto-injected senior-engineer question bank** — inspired by [**Socratic**](https://github.com/m4vic/socratic) (MIT), a self-interrogation skill for agentic AI by [m4vic](https://github.com/m4vic). It ships **697 questions across 15 engineering domains**, distilled from Kleppmann, Nygard, Evans, Ousterhout, Feathers & Khorikov — the questions a senior engineer asks before writing code.

### Why

When you ask Meboya to build, design, migrate, or review something, the LLM normally self-interrogates from **its own memory** — which has blind spots. Socratic loads a **curated question bank** directly into the prompt so the LLM has to confront the *right* questions, not just the ones it happens to remember.

### How it works

| Step | What happens |
|------|-------------|
| 1. Detect | `pre_llm_call` scans your message for build/design/migrate/review signals (`bikin`, `bangun`, `migrasi`, `design`, `review`, …) |
| 2. Map | A signal-word map selects the relevant engineering domains (e.g. `API` + `auth` → 04-api + 05-security) |
| 3. Inject | The question files for those domains (Core mode, ~600 tokens) are appended to the prompt — **no tool call, no LLM round-trip** |
| 4. Self-answer | LLM silently answers the questions, folds them into its decision |
| 5. Contract | The LLM emits a `Domains considered / Self-answered / Assumed / Open questions / Risks / Plan` contract **inside `<world_model>`** before `[DECISION]` |

### Why it's better than before

| | Before (Meboya alone) | After (Meboya + Socratic) |
|---|---|---|
| Question source | LLM memory — blind spots | 697-question bank, curated from systems books |
| Coverage | Whatever the model recalls | 15 engineering domains, Core/Full depth |
| Load | Always the same guide | Only when task signals engineering work (~600 tokens) |
| Output | Hats → [DECISION] | Hats → contract → [DECISION] |
| Chat turns | — | 0 extra tokens (no trigger → no injection) |

### The contract output

```
Domains considered:   requirements, api, security, testing
Self-answered:        JWT over session (stateless, existing infra), scoped tokens
Assumed (flag if wrong): single-region; no PII in claims
Open questions for you: 1. Is 30-day token lifetime acceptable?
Top risks:            no refresh-token rotation — add if long-lived sessions needed
Plan:                 middleware → issuer → verify → test
```

The point is not to ask *more* questions — it's to ask the **most useful** ones at the right time without burning context. Non-build turns cost **0 extra tokens**; build turns cost ~600 tokens (measured with `tiktoken o200k_base`).

### Telemetry

`/meboya status` tracks real-world effectiveness:

```
Socratic: ON
  triggered:      12 turns
  contract emitted: 10/12 (83%)
  tokens injected: ~7,400
```

- **Trigger rate** — how often engineering tasks appear
- **Contract rate** — of triggered turns, how many actually emit the contract (≥50% = working)
- **Tokens injected** — total context cost

---

## Installation

```bash
# Via Hermes CLI (recommended)
hermes plugins install prajadiputra/Meboya

# Or clone manually
git clone https://github.com/prajadiputra/Meboya.git
cp -r Meboya ~/.hermes/plugins/meboya
```

Enable in `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - meboya
```

Restart:

```bash
hermes gateway restart
```

### Verify

```
/meboya status
```

Expected output:

```
Meboya v2.7.5
  Enabled: True
  Mode: auto
  Depth: 3 (1=concise, 2=hats, 3=hats+reason_deeper)
  Hats: ON
  Show: ON
  Critical: ON
  Mnemosyne: Y
  MC iters: 10,000
  Max recursion: 3
  reason_deeper: 0 calls, 0 ignored
  Hard-break: OFF
  Socratic: ON
    triggered: 12 turns
    contract emitted: 10/12 (83%)
    tokens injected: ~7,400
```

---

## Update

```bash
hermes plugins update meboya
hermes gateway restart
```

Or fresh re-install:

```bash
rm -rf ~/.hermes/plugins/meboya
hermes plugins install prajadiputra/Meboya
hermes plugins enable meboya
hermes gateway restart
```

---

## How Output Looks

### Show (default)

Full hats visible (inside `<world_model>` per injection):

```
<world_model>
[WHITE] facts
[BLACK] risks
  ├ CRITICAL: hardest pushback
[RED] gut reaction
[YELLOW] benefits
[GREEN] alternatives
  ├ CRITICAL: what's the opposite approach?
[BLUE] synthesis
  ├ CRITICAL: second-order effects?
</world_model>

[DECISION]
- Decision: ...
- Key Reason: ...
- Risk Accepted: ...
- Action: ...

Dynamic follow-up question
```

### Hide

Decision-only — reasoning still runs:

```
[DECISION]
- Decision: ...
- Key Reason: ...
- Risk Accepted: ...
- Action: ...

Dynamic follow-up question
```

---

## Commands (complete reference)

### Core

| Command | Description |
|---|---|
| `/meboya on` | Enable Meboya thinking injection |
| `/meboya off` | Disable Meboya thinking injection |
| `/meboya status` | Show current state and settings |
| `/meboya reset` | Reset reason_deeper counters + hard-break |

### Depth Control

| Command | Description |
|---|---|
| `/meboya auto` | Automatic depth per query (default — complexity→depth) |
| `/meboya manual low` | Force depth 1 (concise analysis, no hats) |
| `/meboya manual medium` | Force depth 2 (hats + decision) |
| `/meboya manual high` | Force depth 3 (hats + reason_deeper hint) |
| `/meboya depth 1` | Same as manual low (shortcut) |
| `/meboya depth 2` | Same as manual medium (shortcut) |
| `/meboya depth 3` | Same as manual high (shortcut) |

### Display (DOGA-compatible)

| Command | Description |
|---|---|
| `/meboya show` | Full hats + world_model visible (default) |
| `/meboya hide` | Decision-only — reasoning still runs, panel hidden |
| `/meboya hats on` | Enable Six Thinking Hats (default on) |
| `/meboya hats off` | Disable hats — concise analysis + decision only |

### Reasoning

| Command | Description |
|---|---|
| `/meboya critical on` | Enable adversarial pushback (├ CRITICAL: sub-points) |
| `/meboya critical off` | Disable critical pushback |
| `/meboya max_recursion 1-5` | Max recursion depth for reason_deeper tool (default: 3) |
| `/meboya mc 1000-50000` | Set Monte Carlo simulation iterations (default: 10000) |
| `/meboya hard-break on` | Manually enable hard-break (blocks reason_deeper) |
| `/meboya hard-break off` | Manually disable hard-break |

### Socratic

| Command | Description |
|---|---|
| `/meboya socratic on` | Enable Socratic question-bank injection (default) |
| `/meboya socratic off` | Disable Socratic injection — hats only |
| `/meboya socratic` | Show current Socratic state |

### Memory (requires Mnemosyne)

| Command | Description |
|---|---|
| `/meboya memory on` | Enable goal memory (controlled via config.yaml) |
| `/meboya memory off` | Disable goal memory |
| `/meboya recall` | Show past query patterns from Mnemosyne |

---

## Built-in Tool: `reason_deeper`

When depth=3, the model can invoke `reason_deeper` for recursive self-critique.

**Parameters:**

| Parameter | Type | Default | Values |
|---|---|---|---|
| `level` | integer | 2 | 1-3 (intensity) |
| `focus` | string | `"black hat"` | `black hat`, `green hat`, `red hat`, `blue hat` |
| `scenarios` | string | `""` | JSON list of `[label, probability]` pairs for Monte Carlo |

**Example:**
```json
{
  "level": 2,
  "focus": "black hat",
  "scenarios": "[["option_a", 0.6], ["option_b", 0.4]]"
}
```

**Output:**
```
[reason_deeper black hat]
Worst-case missed?
MC(20000): Winner=option_a, conf=20.0%
[end]
```

**Hard-break:** After 3 consecutive calls where the model ignores `reason_deeper` output, hard-break auto-activates and blocks further calls. Reset with `/meboya reset`.

---

## Critical Mode (Default ON)

Critical mode adds `├ CRITICAL:` sub-points to BLACK, GREEN, and BLUE hats:

| Hat | Standard | Critical |
|---|---|---|
| [BLACK] | Risks, edge cases | + "Is premise valid? Hidden costs?" |
| [RED] | Gut reaction | (unchanged — already subjective) |
| [GREEN] | Alternatives | + "What's the OPPOSITE approach?" |
| [BLUE] | Synthesis | + "Best answer or easiest? 2nd-order effects?" |

---

## Architecture

```
User message
  │
  ▼
pre_llm_call hook:
  ├── Detect complexity → auto-depth
  ├── Inject thinking guide (Six Hats + Critical + Decision)
  └── Return injected prompt with ---MEBOYA: marker
  │
  ▼
LLM responds with hats inside <world_model>
  │
  ▼
transform_llm_output hook:
  ├── show: pass through full response
  ├── hide: strip <world_model>, keep [DECISION]
  └── fallback: if hats leak outside <world_model>, cut from [DECISION]
  │
  ▼
post_llm_call hook:
  ├── Detect goal type from response
  ├── Save to Mnemosyne (if available)
  └── Track reason_deeper ignore count → hard-break
  │
  ▼
Response delivered to user (show: full, hide: decision-only)
```

---

## Knowledge Graph

Generated with [graphify](https://github.com/Graphify-Labs/graphify) — local AST parsing, **0 LLM tokens**. Artifacts in [`graphify-out/`](graphify-out/) (`graph.json`, `graph.html`, [`GRAPH_REPORT.md`](graphify-out/GRAPH_REPORT.md)).

**31 nodes · 49 edges · 9 communities · 92% EXTRACTED / 8% INFERRED** (built from commit `ee293bf`)

### God Nodes (core abstractions, by degree)

| # | Node | Edges | Role |
|---|---|---|---|
| 1 | `register()` | 7 | Entry point — mounts 3 hooks + tool + command |
| 2 | `_on_post_llm_call()` | 6 | Detect complexity + `_remember()` + hard-break + socratic telemetry |
| 3 | `_on_pre_llm_call()` | 5 | Inject hat guide + socratic question bank |
| 4 | `_Ctx` | 5 | Test harness context (register_hook/tool/command) |
| 5 | `_socratic_injection()` | 4 | Signal detection + domain mapping + question-bank injection |
| 6 | `_format_show_hide()` | 4 | Strip `<world_model>`, keep `[DECISION]` |
| 7 | `_on_transform_llm_output()` | 4 | Show/hide dispatch |
| 8 | `reason_deeper()` | 4 | Recursive self-critique tool |
| 9 | `_cmd()` | 4 | `/meboya` command handler |
| 10 | `_detect_complexity()` | 3 | Auto-depth heuristic |

### Communities (top 4 of 9)

| Community | Cohesion | Members |
|---|---|---|
| **Commands & State** (`__init__.py`) | 0.50 | `_cmd`, `_recall`, `_State` |
| **Reasoning Tools** (`test_trace_hats.py`) | 0.60 | `monte_carlo_simulate`, `reason_deeper`, `register` |
| **Show/Hide** | 0.50 | `_format_show_hide`, `_on_transform_llm_output` |
| **Socratic** | 0.67 | `_socratic_injection`, `_socratic_read` |

5 thin communities (<3 nodes) omitted — see `graphify-out/GRAPH_REPORT.md` full report.

### Flow (register → hooks)

```
register()
  ├─indirect_call→ _on_pre_llm_call()        (bridges community 6 → 1)
  ├─indirect_call→ _on_post_llm_call()
  ├─indirect_call→ _on_transform_llm_output()
  └─call→         reason_deeper()            (bridges community 3 → 1)

_on_transform_llm_output() ─call→ _format_show_hide()
_on_post_llm_call()        ─call→ _detect_complexity(), _remember()
_cmd()                     ─call→ _recall()
```

Rebuild after code changes:

```bash
# From repo root
graphify . --code-only --out graphify-out
graphify cluster-only /tmp/meboya-git
```

---

## Mnemosyne Memory (Optional)

```bash
pip install mnemosyne-memory
```

Meboya auto-detects Mnemosyne at runtime:

| Without Mnemosyne | With Mnemosyne |
|---|---|
| Works standalone | Recalls past query patterns |
| No memory across sessions | Saves goal_type, complexity, depth |
| `/meboya recall` = empty | Shows past goal patterns |
| Status = `N` | Status = `Y` |

---

## Origin

Inspired by **[DOGA](https://github.com/0z1-ghb/doga-hermes)** — the original Hermes thinking layer plugin by 0z1-ghb.

Meboya ports DOGA's reasoning architecture (show/hide via `transform_llm_output`, Monte Carlo, recursive reasoning, Six Hats) while adding critical mode, hard-break, and auto-depth — all in a single-file plugin with zero hard dependencies.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Unknown command: /meboya` | `hermes plugins enable meboya` + restart gateway |
| No hat tags in response | Check plugin enabled + not disabled via `hats off`. Restart gateway — fresh session picks up new guide |
| Hats never appear in CLI | Ensure no other plugin strips/redirects the request (e.g. old agy-router). Remove conflicting plugins, restart |
| `[Thinking Guide]` / `[PAST CONTEXT]` in output | Update to v2.4.3+ (silent wrappers) |
| Hide still shows hats | Update to v2.6.3+ (fallback strip from [DECISION]) |
| Model got `tools[X].function.function` 400 error | Update to v2.6.1+ (schema double-wrap fix) |
| `reason_deeper` not working | Check depth ≥ 3, hard-break off |
| Trace vanished after update | Run `git checkout -- . && git pull` in plugin dir |
| Gateway 400 via LimitRouter + Qwen | Not Meboya — 9router v0.5.40 injects `enable_thinking`. Workaround: remove Qwen from 9router combo. See [issue #2752](https://github.com/decolua/9router/issues/2752). |
| Prompt "replace built-in tools" | `plugin.yaml` is clean — answer `n` (not needed) |

---

## Development

See [`DEVELOP_GUIDE.md`](DEVELOP_GUIDE.md) for boundary rules, release checklist, and test harness.

```bash
python3 test_trace_hats.py  # must pass before every commit
```

---

## License

MIT

---

## Credits

- **[DOGA](https://github.com/0z1-ghb/doga-hermes)** (0z1-ghb) — original thinking layer plugin and architecture reference
- **[Socratic](https://github.com/m4vic/socratic)** (m4vic) — 697-question senior-engineer question bank, MIT — source of the Socratic enhancement
- **Six Thinking Hats** (Edward de Bono, 1985)
- **[Mnemosyne](https://github.com/mnemosyne-oss/mnemosyne)** — memory layer for AI agents
- **[Hermes Agent](https://github.com/NousResearch/hermes-agent)** — the platform
