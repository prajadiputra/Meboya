# Meboya 🔍

> **Bali: *meboya* = "questioning everything"**  
> Auto-thinking plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent) — structured reasoning with Six Thinking Hats + Critical mode + decision summary.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.7.1-green)](https://github.com/prajadiputra/Meboya/releases)

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
| ❓ **Socratic Enhancement** | Auto-injects a curated senior-engineer question bank (~15 domains) when the task signals build/design/migrate/review work |

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

### Commands

| Command | Description |
|---------|-------------|
| `/meboya socratic on` | Enable Socratic enhancement |
| `/meboya socratic off` | Disable Socratic enhancement |
| `/meboya status` | Shows Socratic state + telemetry (triggered turns, contract rate, tokens) |

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

## Commands

| Command | Description |
|---------|-------------|
| `/meboya status` | Show current state (incl. Socratic telemetry) |
| `/meboya on` | Enable Meboya |
| `/meboya off` | Disable Meboya |
| `/meboya depth 1/2/3` | Set thinking depth |
| `/meboya critical on/off` | Toggle critical analysys |
| `/meboya recall` | Show past patterns from Mnemosyne |
| `/meboya socratic on/off` | Toggle Socratic enhancement |

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
- **[Socratic](https://github.com/m4vic/socratic)** (m4vic) — 697-question senior-engineer question bank, MIT — source of the Socratic enhancement
- **Six Thinking Hats** (Edward de Bono, 1985)
- **[Mnemosyne](https://github.com/mnemosyne-oss/mnemosyne)** — memory layer for AI agents
- **[hermes-pda](https://github.com/carbongotfound/hermes-pda)** — critical thinking inspiration
