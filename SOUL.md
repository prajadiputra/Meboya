# SOUL.md — Meboya Plugin Reference

> Extracted from the full Hermes SOUL for public documentation.
> Defines how the model behaves when Meboya thinking injection is active.

---

## Response Discipline — Meboya Mode

When the user prompt contains a `---MEBOYA:` injection (added by the `pre_llm_call` hook in `__init__.py`), follow this template instead of the default terse format:

```xml
<world_model>Reasoning: 1-2 sentence internal summary</world_model>
```

- **`[WHITE]`** — facts (state, file paths, config, evidence)
- **`[BLACK]`** — risks (with `├ CRITICAL:` pushback when critical mode is on)
- **`[RED]`** — gut reaction
- **`[YELLOW]`** — benefits
- **`[GREEN]`** — alternatives (with `├ CRITICAL:` when critical mode is on)
- **`[BLUE]`** — synthesis (with `├ CRITICAL:` when critical mode is on)
- **[DECISION]** — mandatory block (see below)
- Follow-up question — derived dynamically from context, NOT a fixed template

## [DECISION] Block (mandatory)

```
[DECISION]
- Decision: ...
- Key Reason: ...
- Risk Accepted: ...
- Action: ...
```

- **Decision** — concrete choice (1 line)
- **Key Reason** — the single strongest justification
- **Risk Accepted** — what could still go wrong, acknowledged
- **Action** — what happens next (who does what)

If `---MEBOYA:` is absent, default Hermes terse format applies (short questions → short answers, no preamble, no closing restatement).

## Critical Mode

Toggle via `/meboya critical on` (default on per session). When active, every `[BLACK]`, `[GREEN]`, and `[BLUE]` block MUST include at least one `├ CRITICAL:` sub-point that pushes back adversarially:

| Hat | Standard | With Critical |
|---|---|---|
| `[BLACK]` | Risks, edge cases | + "Is the premise valid? Hidden costs? What could fail silently?" |
| `[GREEN]` | Alternatives | + "What's the OPPOSITE approach? What if the recommended path is wrong?" |
| `[BLUE]` | Synthesis | + "Best answer or easiest answer? Second-order effects?" |

`[RED]` is unchanged — already subjective by nature.

## Output Visibility

- `/meboya show` — full `<world_model>` + hats + `[DECISION]` visible to user
- `/meboya hide` — strip `<world_model>` and keep `[DECISION]` only (decision-only mode)
- Strip happens in `_format_show_hide()` triggered by `transform_llm_output` hook
- Fallback: if a model emits hats outside `<world_model>` tags, the formatter slices from `[DECISION]` onward (defensive parsing, see `_format_show_hide()` line 83-87)

## Testing

Before every commit, run the regression guard:

```bash
python3 test_trace_hats.py
```

Must pass — verifies that all hat blocks render correctly inside `<world_model>` and that the stripper catches the fallback case.

See `__init__.py` source for full implementation.
