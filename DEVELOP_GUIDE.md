# DEVELOPMENT GUIDE — MEBOYA (DO NOT BREAK)

This is a boundary file for AI assistant development. Read before every Meboya change.

---

## ❌ DO NOT TOUCH (Breaking any of these = regression)

### Trace Hat Injection
- `pre_llm_call` MUST return injection with `[WHITE]`, `[BLACK]`, `[YELLOW]`, `[GREEN]`, `[BLUE]`
- `[DECISION]` block with Decision/Key Reason/Risk Accepted/Action
- `├ CRITICAL:` sub-points in BLACK/GREEN/BLUE (when critical_mode=True)
- `<world_model>` block (goal + complexity + scenarios)
- Follow-up question after [DECISION] (dynamic, LLM-determined, NOT template)

### Plugin Infrastructure
- `register()` function — MUST call `ctx.register_hook("pre_llm_call", ...)` and `ctx.register_tool("reason_deeper", ...)`
- `ctx.register_command(name="meboya", handler=_cmd, ...)`
- `plugin.yaml` — NO `provides_hooks`, NO `tools:` (causes security prompt "replace built-in tools")
- Function signatures: `_on_pre_llm_call(**_: Any)`, `_cmd(a: str, **_: Any)`

### State
- `_state.enabled` default `True`
- `_state.depth` default `3`
- `_state.critical_mode` default `True`
- `_state.hard_break` default `False`
- `_state.rd_calls`, `_state.rd_ignored` default `0`

---

## ✅ SAFE TO CHANGE

- Prompt wording (INSTRUCTION / CRITICAL_INSTRUCTION) — as long as test_trace_hats.py still passes
- Monte Carlo iterations (`_state.mc_iters`)
- Depth levels (currently 1-3, can expand)
- Command handlers (add new subcommands to `_cmd`)
- Version string in status/logger
- Complexity detection keywords

---

## 🧪 MANDATORY: RUN TEST BEFORE COMMIT

```bash
python3 test_trace_hats.py
```

Must return: `✅ ALL TRACE HATS TESTS PASSED`

If it returns `❌ N FAILURES`:
1. Read the failure messages
2. Fix the code
3. Run test again
4. Only commit when test passes

---

## 🔧 COMMON MISTAKES (learned the hard way)

### 1. `_recall()` wrapper signature
```python
def _recall(q, k=3):  # wrapper param is 'k'
    return _mnemosyne.recall(q, top_k=k)  # Mnemosyne API uses 'top_k'
```
Call as: `_recall(user_message, k=2)` — NOT `_recall(user_message, top_k=2)`
The wrapper uses `k`, the Mnemosyne API uses `top_k`.

### 2. Never remove trace markers
- `[WHITE] [BLACK] [YELLOW] [GREEN] [BLUE] [DECISION]` are required in EVERY response
- Removing them = regression = user angry
- If you want to change format, keep ALL tags present, just change wording

### 3. `pre_llm_call` return = injection into user message
- String returned = appended to user message content
- Model may echo the injection if it's too long
- Keep instructions SHORT (1-3 lines max)
- If model echoes, REDUCE length, don't add more content

### 4. Plugin path: `~/.hermes/plugins/meboya/__init__.py`
- Gateway loads from THIS file, not from the repo
- After pushing to repo, must `hermes plugins update meboya` + `hermes gateway restart`
- Never edit active plugin directly — always edit repo, push, then update

### 5. `plugin.yaml` restrictions
- NO `provides_hooks:` — Hermes auto-discovers hooks from `register()`
- NO `tools:` — causes "replace built-in tools" security prompt
- Only: name, version, description, author, license, homepage

---

## 📋 RELEASE CHECKLIST

After every commit:
1. `python3 test_trace_hats.py` → ✅ PASSED
2. `cp __init__.py` to repo
3. `git add -A && git commit`
4. `git push origin main`
5. Update version string in status/logger
6. `git tag -a vX.Y.Z`
7. `git push origin vX.Y.Z`
8. `gh release create vX.Y.Z --title "..." --notes "..."`
