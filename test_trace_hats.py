"""Meboya trace hats regression test.
Run BEFORE every commit to verify [WHITE]...[BLUE] + [DECISION] are injected.
"""
import re, sys, json

sys.path.insert(0, '.')
from __init__ import (
    _on_pre_llm_call, _on_post_llm_call,
    _cmd, monte_carlo_simulate, _state
)

errors = []

# 1. Verify hooks do not crash
try:
    result = _on_pre_llm_call(user_message="test query for cloud provider comparison", is_first_turn=False)
    if result is None:
        errors.append("FAIL: _on_pre_llm_call returned None (injection skipped)")
    else:
        # Check hats in injection
        for tag in ["[WHITE]", "[BLACK]", "[YELLOW]", "[GREEN]", "[BLUE]", "[DECISION]"]:
            if tag not in result:
                errors.append(f"FAIL: Injection missing {tag}")
        # Check CRITICAL tags (when critical mode on)
        if _state.critical and "├ CRITICAL" not in result:
            errors.append(f"FAIL: Critical mode ON but injection missing ├ CRITICAL")
        # Check follow-up instruction
        if "follow-up" not in result:
            errors.append(f"FAIL: Missing follow-up question instruction")
        # Check <world_model>
        if "<world_model>" not in result:
            errors.append(f"WARN: <world_model> not found in injection")
except Exception as e:
    errors.append(f"CRASH: _on_pre_llm_call raised {e}")

# 2. Verify post hook does not crash
try:
    _on_post_llm_call(response_text="[WHITE] test [BLACK] test [DECISION] test")
except Exception as e:
    errors.append(f"CRASH: _on_post_llm_call raised {e}")

# 3. Verify _cmd('status') contains a semantic version (invariant, not snapshot)
try:
    status = _cmd('status')
    if not re.search(r"Meboya v\d+\.\d+\.\d+", status):
        errors.append("FAIL: Status missing semantic version string")
except Exception as e:
    errors.append(f"CRASH: _cmd('status') raised {e}")

# 4. Verify Monte Carlo engine
try:
    r = monte_carlo_simulate([('A', 0.6), ('B', 0.4)], 1000, seed=1)
    if 'winner' not in r or 'confidence' not in r:
        errors.append("FAIL: Monte Carlo missing keys in return")
except Exception as e:
    errors.append(f"CRASH: monte_carlo_simulate raised {e}")

# 5. Verify reason_deeper
try:
    from __init__ import reason_deeper
    rd = reason_deeper(level=2, focus="black hat")
    if "[reason_deeper" not in rd:
        errors.append(f"FAIL: reason_deeper returned unexpected: {rd[:60]}")
except Exception as e:
    errors.append(f"CRASH: reason_deeper raised {e}")

# 6. Verify hide strips hats even when model ignores <world_model> wrapper
try:
    from __init__ import _format_show_hide
    _state.show_mode = False
    telegram_like = """[WHITE] facts
[BLACK] risks
[RED] gut
[YELLOW] benefits
[GREEN] alternatives
[BLUE] synthesis

[DECISION]
- Decision: concise
- Key Reason: test
- Risk Accepted: none
- Action: done

Follow-up?"""
    hidden = _format_show_hide(telegram_like)
    if any(tag in hidden for tag in ("[WHITE]", "[BLACK]", "[RED]", "[YELLOW]", "[GREEN]", "[BLUE]")):
        errors.append("FAIL: hide leaked hat blocks outside <world_model>")
    if "[DECISION]" not in hidden or "Follow-up?" not in hidden:
        errors.append("FAIL: hide removed decision or follow-up")
finally:
    _state.show_mode = True

# 7. Verify tool schema not double-wrapped
# Bug: Meboya v2.6.0 passed {"type":"function","function":{...}} →
# Hermes wraps again → tools[N].function.function/type → LimitRouter 400
try:
    class _Ctx:
        def __init__(self): self.tools={}
        def register_hook(self,*a,**k): pass
        def register_command(self,*a,**k): pass
        def register_tool(self, name, toolset=None, schema=None, handler=None, **k):
            self.tools[name]=schema
    from __init__ import register
    ctx=_Ctx(); register(ctx)
    for tname, s in ctx.tools.items():
        if not isinstance(s, dict):
            errors.append(f"FAIL: tool {tname} schema not dict")
            continue
        sks = set(s.keys())
        if not {'name','description','parameters'} <= sks:
            errors.append(f"FAIL: tool {tname} missing keys: {sks}")
        if 'function' in s or 'type' in s:
            errors.append(f"FAIL: tool {tname} double-wrapped — Has {sorted(s.keys())}")
except Exception as e:
    errors.append(f"CRASH: schema double-wrap check raised {e}")

# Report
if errors:
    for e in errors:
        print(f"  {e}")
    print(f"\n❌ {len(errors)} FAILURES — fix before commit!\n")
    sys.exit(1)
else:
    print("✅ ALL TRACE HATS TESTS PASSED — safe to commit")
    sys.exit(0)
