# Meboya

> **Bali: *meboya* = "questioning everything"**  
> An auto-thinking plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent) that makes every response more structured, mindful, and evidence-aware — automatically.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![Hermes Plugin](https://img.shields.io/badge/Hermes-Plugin-purple)](https://github.com/NousResearch/hermes-agent)
[![Version](https://img.shields.io/badge/version-2.1.0-green)](https://github.com/prajadiputra/Meboya/releases)

---

## What Meboya Does

- **Goal Detection** — identifies if user wants Information / Understanding / Action
- **Six Thinking Hats** — structured parallel thinking: facts → risks → benefits → alternatives → synthesis
- **Critical Mode** — optional adversarial pushback on premises, conclusions, and second-order effects
- **Memory Recall** — injects past goal patterns from Mnemosyne for context-aware responses
- **Memory Write** — persists each query + detected goal/complexity for future recall  
- **Auto-Depth** — chooses thinking depth based on query complexity (0 LLM tokens)
- **Trace Markers** — always-visible 💡 Starting / ✅ Complete markers
- **Zero Dependencies** — pure Python stdlib, works without Mnemosyne

---

## Installation (Hermes Plugin Standard)

### Option A — Git clone

```bash
git clone https://github.com/prajadiputra/Meboya.git
cp -r Meboya ~/.hermes/plugins/meboya
```

### Option B — Hermes plugin install

```bash
hermes plugins install prajadiputra/Meboya
```

### Enable the plugin

```yaml
# ~/.hermes/config.yaml
plugins:
  enabled:
    - meboya
```

Then restart:

```bash
hermes gateway restart
```

### Verify

```
/meboya status
```

---

## What Happens After Install

Every response will show:

```
💡 **Meboya: Starting thinking process...**

**Mode:** Goal Detection + Six Thinking Hats
**Depth:** 2 | **Complexity:** medium
🎩 **Hats used:** WHITE → BLACK → YELLOW → GREEN → BLUE
✅ **Meboya: Thinking process complete. Summary ready.**
---

[actual response with hat tags]
```

---

## Slash Commands

| Command | Description |
|---------|-------------|
| `/meboya status` | Show current state |
| `/meboya on` | Enable Meboya (default) |
| `/meboya off` | Disable Meboya |
| `/meboya depth 1` | Goal detection only |
| `/meboya depth 2` | Goal + Six Hats (default) |
| `/meboya depth 3` | Depth 2 + `reason_deeper` |
| `/meboya critical on` | Enable adversarial pushback reasoning |
| `/meboya critical off` | Disable (default) |
| `/meboya markers on/off` | Toggle injection markers |
| `/meboya trace on/off` | Toggle trace display |
| `/meboya recall` | Show recent goal patterns |

---

## Critical Mode (NEW in v2.1.0)

Critical mode adds analytical pushback to the thinking process. It does NOT change agent personality — it adds structured challenge questions within the existing hat framework.

**When ON, the hats deepen:**

| Hat | Normal | Critical |
|-----|--------|----------|
| [BLACK] | Risks, edge cases, pitfalls | + "Is the premise itself valid? What assumptions may be wrong?" |
| [RED] | Gut reaction, intuition | + "What feels off? Trust the signal." |
| [GREEN] | Alternatives, creative options | + "What is the OPPOSITE approach? Argue against the default." |
| [BLUE] | Synthesize conclusion | + "Is this the BEST answer, or just the easiest acceptable one?" |

**Use case:** Technical decisions where first-pass analysis might miss flaws. Critical mode forces the model to defend its conclusion against counterarguments before delivering it.

**Default:** OFF — Meboya works without it. Enable when you want deeper scrutiny.

---

## How It Works

```
User sends message
  │
  ▼
Meboya hooks: pre_llm_call
  │
  ├── (optional) Recall past goal patterns from Mnemosyne
  ├── Choose prompt based on depth + critical_mode flag
  └── Inject [meboya_guide]:
        Goal Detection + Six Thinking Hats (± Critical pushback)
  │
  ▼
LLM responds with [WHITE]...[BLUE] hat tags
  │
  ▼
Meboya hooks: transform_llm_output
  │
  ├── Strip [meboya_guide] markers
  ├── Detect active hats
  ├── Build trace (always visible)
  └── (optional) Write to Mnemosyne
  │
  ▼
Response delivered to user (with 💡 trace prefix)
```

---

## Mnemosyne Integration (Optional Memory Layer)

Meboya can optionally connect to [Mnemosyne](https://github.com/mnemosyne-oss/mnemosyne) — a universal memory layer for Hermes Agent. This integration is **fully optional**: Meboya works perfectly without it, but with Mnemosyne it gains persistent memory across sessions.

### Install Mnemosyne

```bash
pip install mnemosyne-memory
```

Or via Hermes plugin system:

```bash
hermes plugins install mnemosyne-oss/mnemosyne
```

Repo: [github.com/mnemosyne-oss/mnemosyne](https://github.com/mnemosyne-oss/mnemosyne)

### How Meboya Uses Mnemosyne

Meboya integrates with Mnemosyne through two hooks:

| Hook | What Meboya does with Mnemosyne |
|------|--------------------------------|
| `pre_llm_call` | **Recall** — queries Mnemosyne for past queries with similar intent, injects them as `[PAST CONTEXT]` into the thinking guide so the model can calibrate its response approach |
| `transform_llm_output` | **Write** — after the model responds, Meboya saves the user's query + detected goal type + complexity score to Mnemosyne for future recall |

### What Gets Stored

Each turn, Meboya writes a memory entry with:

- **content**: the user's original message
- **goal_type**: `information` / `understanding` / `action` / `unknown`
- **complexity**: `low` / `medium` / `high` (heuristic score)
- **depth**: current thinking depth (1-3)

### Benefits

| Without Mnemosyne | With Mnemosyne |
|-------------------|----------------|
| Meboya works in isolation, no memory | Meboya remembers past query patterns |
| Each session starts fresh | Similar queries get context-aware calibration |
| `/meboya recall` returns empty | `/meboya recall` shows past goal patterns |
| Status shows `❌ unavailable` | Status shows `✅ connected` |

### Verify Connection

After installing Mnemosyne, restart Hermes and check:

```
/meboya status
```

If `Mnemosyne: ✅ connected` appears, the integration is active. If `❌ unavailable`, Meboya will continue working in standalone mode (no crash, no error — just no memory features).

---

## Origin

Meboya is inspired by **DOGA** — the original probabilistic thinking layer plugin by [0z1-ghb](https://github.com/0z1-ghb/doga-hermes). It was rewritten from scratch with different design priorities:
- Pure stdlib, zero hard dependencies
- Graceful fallback (no crashes)
- Six Thinking Hats + Critical mode
- Always-visible trace markers

---

## Plugin Structure (Hermes Standard)

```
~/.hermes/plugins/meboya/
├── plugin.yaml      # manifest
├── __init__.py      # register() — hooks + commands
└── README.md        # this file
```

**plugin.yaml** — declares hooks:

```yaml
name: meboya
version: "2.1.0"
provides_hooks:
  - pre_llm_call
  - transform_llm_output
```

**register(ctx)** — wires everything:

```python
def register(ctx):
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("transform_llm_output", _on_transform_llm_output)
    ctx.register_command(
        name="meboya",
        handler=_cmd_meboya,  # ← REQUIRED
        description="...",
    )
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/meboya status` = "Unknown command" | Add `handler=_cmd_meboya` to `register_command()` |
| No trace markers appear | `async def` hooks don't work — must be `def` |
| Plugin loads but hooks don't fire | Clear `__pycache__` + kill all hermes processes |
| `[meboya_guide]` appears in output | `transform_llm_output` not running — check `provides_hooks` in plugin.yaml |

---

## License

MIT

---

## Credits

- **DOGA** (0z1-ghb) — the original Hermes thinking layer plugin
- **Six Thinking Hats** (Edward de Bono, 1985)
- **Mnemosyne** (Mnemosyne-OSS) — universal memory layer for AI agents
- **hermes-pda** (carbongotfound) — critical thinking inspiration
