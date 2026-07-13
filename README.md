# Meboya 🔍

> **Bali: *meboya* = "questioning everything"**  
> An auto-thinking plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent) that makes every response more structured, mindful, and evidence-aware — automatically.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![Hermes Plugin](https://img.shields.io/badge/Hermes-Plugin-purple)](https://github.com/NousResearch/hermes-agent)

---

## Why Meboya?

LLMs are trained to answer instantly. That's good for trivial queries but problematic for decisions — they rarely pause to consider alternatives, risks, or missing information.

Meboya is an evolution of the **DOGA plugin**, redesigned from scratch:
- **Zero dependencies** — pure Python stdlib, no AST whitelists, no fragile imports
- **Graceful Mnemosyne fallback** — works with or without memory
- **Structured lenses** — De Bono's Six Thinking Hats, not freeform chain-of-thought
- **Auto-recall** — past similar queries shape current responses (if Mnemosyne is present)

---

## Features

| Feature | What it does |
|---------|-------------|
| 🎯 **Goal Detection** | Categorises each query as Information / Understanding / Action |
| 🎩 **Six Thinking Hats** | Enforces structured parallel thinking: facts → risks → benefits → alternatives → synthesis |
| 📚 **Memory Recall** | Injects past goal patterns from Mnemosyne for context-aware responses |
| ✍️ **Memory Write** | Persists each query + detected goal/complexity for future recall |
| 🧠 **Deep Mode** | Depth 2 (default) = goal + hats. Depth 3 = adds `reason_deeper` guidance |
| 🪶 **Zero Deps** | No external packages, no AST parsing, no fragile imports |
| 🛡️ **Graceful Degradation** | Works perfectly without Mnemosyne — memory read/write is optional |
| 🔌 **Drop-in Plugin** | Copy directory, enable in config, done |

---

## Installation

### Quick — copy from repo

```bash
git clone https://github.com/prajadiputra/Meboya.git
cp -r Meboya ~/.hermes/plugins/meboya
```

### Enable in Hermes config

Edit `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - meboya
```

Then restart Hermes:

```bash
hermes gateway restart
```

### Optional: Mnemosyne Integration

Meboya auto-detects Mnemosyne at runtime — no config needed.  
To enable memory persistence:

```bash
pip install mnemosyne-hermes   # or mnemosyne-memory[embeddings]
```

That's it. Meboya will automatically:
- **Recall** past goal patterns on similar queries
- **Persist** each query with detected goal type, complexity, and depth

---

## Usage

Meboya works silently in the background — no interaction needed.  
It injects a structured thinking prompt before every LLM call and strips it before the final response.

### Slash commands

| Command | Description |
|---------|-------------|
| `/thinking status` | Show current state (enabled, depth, Mnemosyne status) |
| `/thinking on` | Enable Meboya (default) |
| `/thinking off` | Disable Meboya — pass-through mode |
| `/thinking depth 1` | Goal detection only |
| `/thinking depth 2` | Goal + Six Hats (default) |
| `/thinking depth 3` | Depth 2 + `reason_deeper` guidance |
| `/thinking markers on\|off` | Toggle `[meboya_guide]` markers in prompt |
| `/thinking recall` | Show recent goal patterns from Mnemosyne |

### Depth levels

| Depth | Prompt | Best for |
|-------|--------|----------|
| **1** | Goal detection only | Simple factual questions |
| **2** (default) | Goal + Six Hats analysis | Decisions, analysis, strategy |
| **3** | Depth 2 + `reason_deeper` guidance | Complex multi-factor problems |

---

## How It Works

```
User sends message
  │
  ▼
Meboya hooks: pre_llm_call
  │
  ├── (optional) Recall past goal patterns from Mnemosyne
  │
  └── Inject [meboya_guide]:
        ┌──────────────────────┐
        │ 1. Goal Detection    │
        │ 2. Six Thinking Hats │
        │ 3. (depth 3) Recurs.│
        └──────────────────────┘
  │
  ▼
Hermes sends prompt to LLM
  │
  ▼
LLM responds with <world_model> reasoning
  │
  ▼
Meboya hooks: transform_llm_output
  │
  ├── Strip [meboya_guide] markers
  │
  ├── Detect goal type + complexity
  │
  └── (optional) Write to Mnemosyne
  │
  ▼
Clean response delivered to user
```

---

## Comparison: Meboya vs DOGA

| Aspect | DOGA | Meboya |
|--------|------|--------|
| **Dependencies** | Mnemosyne + AST | Pure stdlib (optional Mnemosyne) |
| **Crash resilience** | Crashing on import error for `mnemosyne-hermes` shadowing (v3.12+) | Graceful fallback — zero crashes |
| **Thinking structure** | De Bono 5 hats (no Red hat, order not enforced) | Six Hats (White, Black, Yellow, Green, Blue + Red) |
| **Goal detection** | Regex-based | Regex + complexity heuristic |
| **Memory metadata** | goal_type only | goal_type + complexity + depth |
| **Maintenance** | stale since May 2026 | actively maintained |
| **LLM Tool (`simulate`)** | Monte Carlo engine (garbage-in-garbage-out due to LLM's poor probability estimation) | Not included — focus on prompt structure rather than fake simulations |

---

## Running Tests

```bash
python -c "
import importlib.util, sys
sys.path.insert(0, 'path/to/Meboya')
spec = importlib.util.spec_from_file_location('mod', 'path/to/Meboya/__init__.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Verify injection
r = mod._on_pre_llm_call(user_message='Test query', is_first_turn=True)
assert '[meboya_guide]' in (r or '')
print('✅ Injection OK')
"
```

---

## License

MIT — see [LICENSE](LICENSE).

---

## Credits

Inspired by:
- **DOGA** (0z1-ghb) — the original Hermes thinking layer plugin
- **Six Thinking Hats** (Edward de Bono, 1985)
- **Mnemosyne** (Mnemosyne-OSS) — universal memory layer for AI agents

Made with ❤️ by [prajadiputra](https://github.com/prajadiputra)
