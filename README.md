# Meboya 🔍

> **Bali: *meboya* = "questioning everything"**  
> Structured reasoning plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent) — Six Thinking Hats + Critical pushback + DOGA-compatible show/hide + Monte Carlo simulation + recursive self-critique.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.6.3-green)](https://github.com/prajadiputra/Meboya/releases)

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
Meboya v2.6.3
  Enabled: True
  Mode: auto
  Depth: 3 (1=goal, 2=hats, 3=deep+reason_deeper)
  Hats: ON
  Show: ON
  Critical: ON
  Mnemosyne: Y
  MC iters: 10,000
  Max recursion: 3
  reason_deeper: 0 calls, 0 ignored
  Hard-break: OFF
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

Full hats visible:

```
&lt;world_model&gt;Reasoning: 1-2 sentence internal reasoning&lt;/world_model&gt;
[WHITE] facts
[BLACK] risks
  ├ CRITICAL: hardest pushback
[RED] gut reaction
[YELLOW] benefits
[GREEN] alternatives
  ├ CRITICAL: what's the opposite approach?
[BLUE] synthesis
  ├ CRITICAL: second-order effects?

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
| `/meboya auto` | Automatic depth per query (default) |
| `/meboya manual low` | Force depth 1 (goal detection only) |
| `/meboya manual medium` | Force depth 2 (goal + hats) |
| `/meboya manual high` | Force depth 3 (goal + hats + reason_deeper) |
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

## Origín

Inspired by **[DOGA](https://github.com/0z1-ghb/doga-hermes)** — the original Hermes thinking layer plugin by 0z1-ghb.

Meboya ports DOGA's reasoning architecture (show/hide via `transform_llm_output`, Monte Carlo, recursive reasoning, Six Hats) while adding critical mode, hard-break, and auto-depth — all in a single-file plugin with zero hard dependencies.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Unknown command: /meboya` | `hermes plugins enable meboya` + restart gateway |
| No hat tags in response | Restart gateway — fresh session picks up new guide |
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
- **Six Thinking Hats** (Edward de Bono, 1985)
- **[Mnemosyne](https://github.com/mnemosyne-oss/mnemosyne)** — memory layer for AI agents
- **[Hermes Agent](https://github.com/NousResearch/hermes-agent)** — the platform
