# Meboya 🔍

> **Bali: *meboya* = "questioning everything"** — Structured reasoning layer for [Hermes Agent](https://github.com/NousResearch/hermes-agent). Six Thinking Hats + Critical pushback + Socratic question bank + Monte Carlo simulation — all in a single-file plugin.

<p align="center">
  <img src="assets/logo.jpg" alt="Meboya" width="640"/>
</p>

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.7.6-green)](https://github.com/prajadiputra/Meboya/releases)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](test_trace_hats.py)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/prajadiputra/Meboya/pulls)

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [How Output Looks](#how-output-looks)
- [Commands](#commands-complete-reference)
- [Socratic Enhancement](#socratic-enhancement-)
- [Built-in Tool: `reason_deeper`](#built-in-tool-reason_deeper)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [License](#license)
- [Credits](#credits)

---

## Features

| Feature | Description |
|---|---|
| 🎩 **Six Thinking Hats** | `[WHITE]` facts → `[BLACK]` risks → `[RED]` gut → `[YELLOW]` benefits → `[GREEN]` alternatives → `[BLUE]` synthesis |
| 🔍 **Critical Mode** (ON by default) | Adversarial pushback with `├ CRITICAL:` sub-points on BLACK, GREEN, BLUE |
| 📊 **Decision Block** | MANDATORY `[DECISION]` with Decision, Key Reason, Risk Accepted, Action |
| 👁️ **Show / Hide** (DOGA-style) | Toggle trace visibility via `transform_llm_output` — reasoning continues, panel hidden |
| 🎲 **Monte Carlo Simulation** | Pure Python probability engine (1K–50K iterations, 0 LLM tokens) |
| 🔄 **Reason Deeper** | Model can invoke `reason_deeper` tool for recursive self-critique with hat lens |
| 🛑 **Hard-Break** | Auto-blocks `reason_deeper` after 3 consecutive ignored calls |
| ⚡ **Auto-Depth** | Per-query complexity detection (concise / hats / deep, 0 LLM tokens) |
| ❓ **Socratic Enhancement** | Auto-injects curated senior-engineer question bank (15 domains) for build/design/migrate/review tasks |
| 🧠 **Mnemosyne Memory** (optional) | Recalls past queries, saves goal patterns across sessions |
| 🪶 **Zero Hard Dependencies** | Pure Python stdlib — Mnemosyne optional |

---

## Requirements

| Requirement | Version |
|---|---|
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | any recent release (plugin API: `register()` + hooks) |
| Python | 3.10+ |
| Mnemosyne | optional — auto-detected at runtime |

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

### Update

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

## Quick Start

```text
# 1. Verify it's live
/meboya status

# 2. Just chat — hats appear automatically
Bandingkan Redis vs Memcached

# 3. Build/design tasks get the full Socratic treatment
Bikin rencana deploy service ke EKS pakai helm
```

Expected `/meboya status`:

```
Meboya v2.7.6
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

## How Output Looks

### Show (default) — full hats + optional Socratic contract

```text
<world_model>
[WHITE] facts (verified only)
[BLACK] risks
  ├ CRITICAL: hardest pushback
[RED] gut reaction
[YELLOW] benefits
[GREEN] alternatives
  ├ CRITICAL: what's the opposite approach?
[BLUE] synthesis
  ├ CRITICAL: second-order effects?

— CONTRACT — (only when Socratic triggers)
- Domains considered: infra, testing, observability
- Self-answered: ...
- Assumed (flag if wrong): ...
- Open questions for you (0-3): ...
- Top risks: ...
- Plan: ...
</world_model>

[DECISION]
- Decision: ...
- Key Reason: ...
- Risk Accepted: ...
- Action: ...

Dynamic follow-up question
```

### Hide — decision only (reasoning still runs)

```text
[DECISION]
- Decision: ...
- Key Reason: ...
- Risk Accepted: ...
- Action: ...

Dynamic follow-up question
```

### Real-world example (build query, show mode)

From a live test with a deploy-plan request:

```text
<world_model>
[WHITE]
- EKS PRD/STG account IDs (verified memory).
- Nodes CAST AI-managed. Istio mesh + VPA.

[BLACK]
├ CRITICAL: chart belum disebut, jangan tebak nama service/chart.
├ CRITICAL: tanpa deployment strategy, rollback bisa salah arah.
- Image tag immutable = Git SHA, bukan :latest.

[RED]
Chart unknown → rencana harus generik dulu.

[YELLOW]
Helm --atomic rollback otomatis. SHA tag = traceable.

[GREEN]
Alternatif: repo sendiri, Bitnami, atau ArgoCD-managed?
├ CRITICAL: jangan asumsi ArgoCD di cluster ini.

[BLUE]
3 langkah: (1) chart, (2) git-SHA tag, (3) helm --atomic rollback.

— CONTRACT —
- Domains considered: infra, testing, observability
- Self-answered: image tagging = git SHA immutable; rollback = helm --atomic
- Assumed (flag if wrong): service name belum tahu; default rolling strategy. FLAG: kalau perlu canary/DB migration, langkah bertambah.
- Open questions for you (1): nama service + chart?
- Top risks: chart salah pilih; rollback tanpa DB compat
- Plan: terima nama service & chart → keluar perintah helm exact
</world_model>

[DECISION]
- Decision: Rencana deploy helm 3 langkah ringkas.
- Key Reason: helm --atomic rollback otomatis + SHA tag traceable.
- Risk Accepted: asumsi rolling strategy default; DB migration perlu pre/post hook.
- Action: kasih nama service + chart → saya isi perintah helm + values override.

Nama service + chart-nya apa? Ada DB migration saat deploy?
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

## Socratic Enhancement 🧠

**Auto-injected senior-engineer question bank** — inspired by [**Socratic**](https://github.com/m4vic/socratic) (MIT), a self-interrogation skill for agentic AI by [m4vic](https://github.com/m4vic). It ships **697 questions across 15 engineering domains**, distilled from Kleppmann, Nygard, Evans, Ousterhout, Feathers & Khorikov.

### Why

When you ask Meboya to build, design, migrate, or review something, the LLM normally self-interrogates from **its own memory** — which has blind spots. Socratic loads a **curated question bank** directly into the prompt so the LLM has to confront the *right* questions, not just the ones it happens to remember.

### How it works

| Step | What happens |
|------|-------------|
| 1. Detect | `pre_llm_call` scans your message for build/design/migrate/review signals (`bikin`, `bangun`, `migrasi`, `design`, `review`, …) |
| 2. Map | A signal-word map selects the relevant engineering domains (e.g. `API` + `auth` → 04-api + 05-security) |
| 3. Inject | The question files for those domains are appended to the prompt — **no tool call, no LLM round-trip** |
| 4. Self-answer | LLM silently answers the questions, folds them into its decision |
| 5. Contract | The LLM emits a `Domains considered / Self-answered / Assumed / Open questions / Risks / Plan` contract **inside `<world_model>`** before `[DECISION]` |

### Why it's better than before

| | Before (Meboya alone) | After (Meboya + Socratic) |
|---|---|---|
| Question source | LLM memory — blind spots | 697-question bank, curated from systems books |
| Coverage | Whatever the model recalls | 15 engineering domains |
| Load | Always the same guide | Only when task signals engineering work |
| Output | Hats → [DECISION] | Hats → contract → [DECISION] |
| Chat turns | — | 0 extra tokens (no trigger → no injection) |

### Telemetry

`/meboya status` tracks real-world effectiveness:

```
Socratic: ON
  triggered:      12 turns
  contract emitted: 10/12 (83%)
  tokens injected: ~7,400
```

---

## Built-in Tool: `reason_deeper`

When depth=3, the model can invoke `reason_deeper` for recursive self-critique.

**Parameters:**

| Parameter | Type | Default | Values |
|---|---|---|---|
| `level` | integer | 2 | 1-3 (clamped by `max_recursion`) |
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

**Hard-break:** After 3 consecutive turns where the model had `reason_deeper` available but didn't call it, hard-break activates and blocks further calls. Reset with `/meboya reset`.

---

## Architecture

```text
User message
  │
  ▼
pre_llm_call hook:
  ├── Detect complexity → auto-depth
  ├── Inject thinking guide (hats + critical + decision)
  ├── Socratic question bank (if build/design trigger)
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
  ├── Socratic telemetry (contract detected on raw pre-strip text)
  ├── Save to Mnemosyne (if available)
  └── Track reason_deeper ignore streak → hard-break
  │
  ▼
Response delivered (show: full, hide: decision-only)
```

---

## Configuration

All configuration is via `/meboya` subcommands (see [Commands](#commands-complete-reference)). State is in-memory per session.

| Setting | Default | Command |
|---|---|---|
| enabled | `True` | `/meboya on\|off` |
| depth | `3` (auto) | `/meboya auto\|manual\|depth` |
| hats | `True` | `/meboya hats on\|off` |
| show mode | `True` | `/meboya show\|hide` |
| critical | `True` | `/meboya critical on\|off` |
| max_recursion | `3` | `/meboya max_recursion 1-5` |
| MC iterations | `10000` | `/meboya mc 1000-50000` |
| socratic | `True` | `/meboya socratic on\|off` |
| hard-break | `False` | `/meboya hard-break on\|off` |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Unknown command: /meboya` | `hermes plugins enable meboya` + restart gateway |
| No hat tags in response | Check plugin enabled + not disabled via `hats off`. Restart gateway |
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
python3 test_trace_hats.py   # must pass before every commit
python3 test_socratic.py     # must pass before every commit
```

Contributions welcome — open a [PR](https://github.com/prajadiputra/Meboya/pulls) or [issue](https://github.com/prajadiputra/Meboya/issues).

---

## License

[MIT](LICENSE)

---

## Credits

- **[DOGA](https://github.com/0z1-ghb/doga-hermes)** (0z1-ghb) — original thinking layer plugin and architecture reference
- **[Socratic](https://github.com/m4vic/socratic)** (m4vic) — 697-question senior-engineer question bank, MIT — source of the Socratic enhancement
- **Six Thinking Hats** (Edward de Bono, 1985)
- **[Mnemosyne](https://github.com/mnemosyne-oss/mnemosyne)** — memory layer for AI agents
- **[Hermes Agent](https://github.com/NousResearch/hermes-agent)** — the platform
