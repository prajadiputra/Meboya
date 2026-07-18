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

# 3. Verify _cmd('status') contains version
try:
    status = _cmd('status')
    if "v2.5.3" not in status:
        errors.append(f"FAIL: Status missing version string")
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

# Report
if errors:
    for e in errors:
        print(f"  {e}")
    print(f"\n❌ {len(errors)} FAILURES — fix before commit!\n")
    sys.exit(1)
else:
    print("✅ ALL TRACE HATS TESTS PASSED — safe to commit")
    sys.exit(0)
