# Meboya 🔍

> **Bali: *meboya* = "questioning everything"**  
> Auto-thinking plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent) — structured reasoning with Six Thinking Hats + Critical mode + decision summary.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.2.0-green)](https://github.com/prajadiputra/Meboya/releases)

---

## Features

| Feature | What it does |
|---------|-------------|
| 🎯 **Goal Detection** | Identifies if user wants Information / Understanding / Action |
| 🎩 **Six Thinking Hats** | Structured parallel thinking: [WHITE] → [BLACK] → [YELLOW] → [GREEN] → [BLUE] |
| 🔍 **Critical Mode** (ON by default) | Adversarial pushback on premises, alternatives, and conclusions |
| 📊 **Decision Summary** | MANDATORY [SUMMARY] block: Decision Hat, Strategy, Key Reason, Risk Accepted, Next Action |
| 🧠 **Mnemosyne Memory** | Optional: recalls past query patterns, saves goals for future sessions |
| ⚡ **Auto-Depth** | Chooses depth level based on query complexity (0 LLM tokens) |
| 🪶 **Zero Hard Dependencies** | Pure Python stdlib — works without Mnemosyne |

---

## How Output Looks

Every response will show:

```
[WHITE] Facts and data about the question...
[BLACK] Risks, edge cases, pitfalls...
  ├ CRITICAL: Is the premise valid?
[YELLOW] Benefits and opportunities...
[GREEN] Alternative approaches...
  ├ CRITICAL: What would a domain expert do?
[BLUE] Conclusion and recommendation...
  ├ CRITICAL: Is this the BEST answer?
[SUMMARY]
- Decision Hat: BLUE
- Selected Strategy: [chosen option + why]
- Key Reason: [single most important factor]
- Risk Accepted: [risk being taken]
- Next Action: [immediate step]
```

---

## Installation

```bash
# Install via Hermes CLI (recommended)
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

---

## Update

```bash
hermes plugins update meboya
hermes gateway restart
```

Or fresh install:

```bash
rm -rf ~/.hermes/plugins/meboya
hermes plugins install prajadiputra/Meboya
hermes plugins enable meboya
hermes gateway restart
```

---

## Commands

| Command | Description |
|---------|-------------|
| `/meboya status` | Show current state |
| `/meboya on` | Enable Meboya |
| `/meboya off` | Disable Meboya |
| `/meboya depth 1/2/3` | Set thinking depth |
| `/meboya critical on/off` | Toggle critical analysys |
| `/meboya recall` | Show past patterns from Mnemosyne |

Default: `critical_mode=ON`, `depth=3` (deepest).

---

## Critical Mode (Default ON)

Critical mode adds structured challenge questions. It does NOT change agent personality — it enriches hats with analytical pushback.

| Hat | Standard | Critical |
|-----|----------|----------|
| [BLACK] | Risks, edge cases | + "Is premise valid? Hidden requirements?" |
| [RED] | Gut reaction | + "What feels off?" |
| [GREEN] | Alternatives | + "What is the OPPOSITE approach? Domain expert?" |
| [BLUE] | Conclusion | + "Best answer or easiest? Second-order effects?" |

---

## Mnemosyne Memory (Optional)

```bash
# Install Mnemosyne
pip install mnemosyne-memory
# Or via Hermes
hermes plugins install mnemosyne-oss/mnemosyne
```

Meboya auto-detects Mnemosyne at runtime:

| Without Mnemosyne | With Mnemosyne |
|-------------------|----------------|
| Works standalone | Recalls past query patterns |
| No memory across sessions | Saves goal_type, complexity, depth |
| `/meboya recall` = empty | Shows past goal patterns |
| Status = `❌ unavailable` | Status = `✅ connected` |

---

## How It Works

```
User sends message
  │
  ▼
Meboya pre_llm_call hook:
  ├── Detect complexity → auto-depth
  ├── (optional) Recall past patterns from Mnemosyne
  ├── Inject thinking guide (without visible wrapper)
  └── Guide includes: Goal Detection + Six Hats + Critical (if ON) + Summary instruction
  │
  ▼
LLM processes with hat structure
  │
  ▼
Meboya post_llm_call hook:
  ├── Detect goal type from response
  └── Save to Mnemosyne (if available)
  │
  ▼
Response delivered:
  [WHITE] ... [BLACK] ... [YELLOW] ... [GREEN] ... [BLUE] ...
  [SUMMARY]
  - Decision Hat, Strategy, Key Reason, Risk Accepted, Next Action
```

---

## Origin

Inspired by **[DOGA](https://github.com/0z1-ghb/doga-hermes)** — the original Hermes thinking layer plugin.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Unknown command: /meboya` | Enable plugin: `hermes plugins enable meboya` + restart |
| No hat tags in response | Restart gateway — fresh session picks up new guide |
| No [SUMMARY] block | Update to v2.2.0+ (auto prompt) |
| `[Thinking Guide]` in output | Update to v2.2.0+ (wrapper removed) |
| `[PAST CONTEXT]` in output | Update to v2.2.0+ (silent recall) |
| Prompt "replace built-in tools" | `plugin.yaml` is clean — answer `n` (not needed) |

---

## License

MIT

---

## Credits

- **[DOGA](https://github.com/0z1-ghb/doga-hermes)** (0z1-ghb) — original thinking layer plugin
- **Six Thinking Hats** (Edward de Bono, 1985)
- **[Mnemosyne](https://github.com/mnemosyne-oss/mnemosyne)** — memory layer for AI agents
- **[hermes-pda](https://github.com/carbongotfound/hermes-pda)** — critical thinking inspiration
