# DEVELOP_GUIDE.md — MEBOYA (DO NOT BREAK)

Guardrails for AI-assisted development. Read before every change.

---

## ❌ DO NOT TOUCH (Breaking any = regression)

### Trace Hat Injection
- `pre_llm_call` MUST return injection with `[WHITE]`, `[BLACK]`, `[YELLOW]`, `[GREEN]`, `[BLUE]`
- `[DECISION]` block: Decision / Key Reason / Risk Accepted / Action
- `├ CRITICAL:` sub-points in BLACK/GREEN/BLUE when `_state.critical_mode=True`
- `<world_model>` block (goal + complexity + scenarios)
- Follow-up question after `[DECISION]` (dynamic, LLM-determined, NOT template)
- Verify with `python3 test_trace_hats.py` — must pass before commit

### Plugin Infrastructure
- `register()` MUST call `ctx.register_hook("pre_llm_call", ...)` and `ctx.register_tool("reason_deeper", ...)`
- `ctx.register_command(name="meboya", handler=_cmd, ...)`
- `plugin.yaml`: NO `provides_hooks`, NO `tools:` (security prompt)
- Function signatures: `_on_pre_llm_call(**_: Any)`, `_cmd(a: str, **_: Any)`

### State
- `_state.enabled` default `True`
- `_state.depth` default `3`
- `_state.critical_mode` default `True`
- `_state.hard_break` default `False`
- `_state.rd_calls`, `_state.rd_ignored` default `0`

### Version Sync (CRITICAL — root cause of repeated failures)
- **THREE places must match on every release:**
  1. `plugin.yaml` → `version:` field (e.g. `"2.5.5"`)
  2. `__init__.py` → `logger.info("meboya vX.Y.Z loaded")` + `f"Meboya vX.Y.Z\n"` in `_cmd('status')`
  3. `git tag -a vX.Y.Z` + GitHub release
- NEVER bump one without the others. If `plugin.yaml` version is stale, `hermes plugins update` silently skips the update.
- After `git push`, ALWAYS `git tag -a vX.Y.Z` + `git push origin vX.Y.Z` + `gh release create vX.Y.Z`.

---

## ✅ SAFE TO CHANGE
- Prompt wording (INSTRUCTION / CRITICAL_INSTRUCTION) — if test_trace_hats.py passes
- Monte Carlo iterations (`_state.mc_iters`)
- Depth levels (1-3, can expand)
- Command handlers (add subcommands to `_cmd`)
- Complexity detection keywords

---

## 🧪 MANDATORY TEST BEFORE COMMIT
```bash
python3 test_trace_hats.py
```
Must return: `✅ ALL TRACE HATS TESTS PASSED`

On `❌ N FAILURES`: read messages, fix, re-run. Only commit when green.

---

## 🚀 RELEASE PROCEDURE (MANDATORY — NEVER SKIP)

After ANY change to `__init__.py` or `plugin.yaml`:

```bash
# 1. Test
python3 test_trace_hats.py   # must be ✅

# 2. Bump version in THREE places (if not already bumped):
#    - plugin.yaml  → version: "X.Y.Z"
#    - __init__.py  → logger.info("meboya vX.Y.Z loaded")
#    - __init__.py  → f"Meboya vX.Y.Z\n" in _cmd('status')

# 3. Sync to repo
cp ~/.hermes/plugins/meboya/__init__.py ~/Meboya/__init__.py
cp ~/.hermes/plugins/meboya/plugin.yaml ~/Meboya/plugin.yaml

# 4. Commit + push
cd ~/Meboya
git add -A
git commit -m "feat/fix: vX.Y.Z — <what changed>"
git push origin main

# 5. Tag + push tag
git tag -a vX.Y.Z -m "Meboya vX.Y.Z"
git push origin vX.Y.Z

# 6. GitHub release (DO NOT SKIP)
gh release create vX.Y.Z --title "Meboya vX.Y.Z — <short desc>" \
  --notes "## vX.Y.Z
### Changes
- <change 1>
- <change 2>

### Update
\`\`\`bash
hermes plugins update meboya
hermes gateway restart
\`\`\`" --repo prajadiputra/Meboya

# 7. Verify release exists
gh release list --repo prajadiputra/Meboya --limit 3
```

**NEVER say "release pushed" without running step 6.** If `gh release create` is blocked by gateway, create it from Mac terminal immediately after.

---

## 🔧 COMMON MISTAKES (learned the hard way)

### 1. `_recall()` wrapper signature
```python
def _recall(q, k=3):  # wrapper param is 'k'
    return _mnemosyne.recall(q, top_k=k)  # Mnemosyne API uses 'top_k'
```
Call as: `_recall(user_message, k=2)` — NOT `_recall(user_message, top_k=2)`

### 2. Version desync (MOST COMMON FAILURE)
- `plugin.yaml` stuck at `2.1.0` while code is `2.5.5` → `hermes plugins update` skips
- Fix: bump `plugin.yaml` version on EVERY release

### 3. Never remove trace markers
- `[WHITE] [BLACK] [YELLOW] [GREEN] [BLUE] [DECISION]` required in EVERY response
- Removing = regression = user angry

### 4. `pre_llm_call` return = injection into user message
- Keep instructions SHORT (1-3 lines) — model echoes long ones
- If model echoes, REDUCE length

### 5. Plugin path: `~/.hermes/plugins/meboya/__init__.py`
- Gateway loads from THIS file, not repo
- After push: `hermes plugins update meboya` + `hermes gateway restart`
- Never edit active plugin directly — edit repo, push, then update

### 6. `plugin.yaml` restrictions
- NO `provides_hooks:` — Hermes auto-discovers from `register()`
- NO `tools:` — causes "replace built-in tools" security prompt
- Only: name, version, description, author, license, homepage

### 7. Soul.md conflict (ultra-terse vs Meboya format)
- SOUL.md §3.1 has Meboya exception — ultra-terse does NOT apply to hat sections
- SOUL.md §11 documents Meboya output format
- If soul.md changes, re-sync to repo SOUL.md

---

## 📋 PRE-COMMIT CHECKLIST
- [ ] `python3 test_trace_hats.py` → ✅ PASSED
- [ ] `plugin.yaml` version bumped (if release)
- [ ] `__init__.py` version string bumped (if release)
- [ ] `cp` to repo + `git commit` + `git push origin main`
- [ ] `git tag -a vX.Y.Z` + `git push origin vX.Y.Z`
- [ ] `gh release create vX.Y.Z` (NEVER SKIP)
- [ ] Verify `gh release list` shows new tag
