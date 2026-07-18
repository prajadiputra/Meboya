"""Meboya — questioning everything. Thinking layer for Hermes Agent."""
from __future__ import annotations
import json, logging, math, random, re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MNEMOSYNE_AVAILABLE = False
_mnemosyne = None
try:
    from mnemosyne import Mnemosyne
    _mnemosyne = Mnemosyne(); MNEMOSYNE_AVAILABLE = True
except Exception:
    pass

def _remember(content, importance=0.7, source="meboya", metadata=None):
    if not MNEMOSYNE_AVAILABLE: return None
    try:
        return _mnemosyne.remember(content=content, importance=importance, source=source, metadata=metadata or {})
    except Exception as e:
        logger.debug("meboya: remember failed: %s", e)
        return None

def _recall(query, top_k=3):
    if not MNEMOSYNE_AVAILABLE: return []
    try: return _mnemosyne.recall(query, top_k=top_k) or []
    except Exception: return []

def _detect_complexity(text):
    low = sum(kw in text.lower() for kw in ("simple","trivial","what is","who is","define"))
    high = sum(kw in text.lower() for kw in ("deploy","architecture","migrate","security","cost","scale"))
    if high >= 2: return ("high", min(80+high*5,99))
    if low >= 2: return ("low", min(20+low*5,40))
    return ("medium", 50)

def monte_carlo_simulate(scenarios, iterations=10000, seed=None):
    if not scenarios: return {"winner":"none","error":"no scenarios"}
    iters = max(1000, min(iterations, 50000))
    labels = [s[0] for s in scenarios]
    weights = [max(s[1],0.01) for s in scenarios]
    probs = [w/sum(weights) for w in weights]
    rng = random.Random(seed) if seed else random.Random()
    counts = [0]*len(labels)
    for _ in range(iters):
        r = rng.random(); acc = 0.0
        for i,p in enumerate(probs):
            acc += p
            if r <= acc: counts[i]+=1; break
    final = [c/iters for c in counts]
    idx = sorted(enumerate(final), key=lambda x:-x[1])
    return {
        "probabilities": {labels[i]: round(final[i],4) for i in range(len(labels))},
        "winner": labels[idx[0][0]],
        "confidence": round(idx[0][1]-(idx[1][1] if len(idx)>1 else 0),4),
        "iterations": iters,
    }

# ── PROMPTS ──

GUIDE = """Meboya thinking: 1) GOAL (Info/Understand/Action) 2) SCENARIOS (2-3 weighted) 3) HATS (White/Black/Red/Yellow/Green/Blue) 4) DECISION + Action. Critical=on means add ├ CRITICAL pushback on each hat. Depth=3 calls reason_deeper()."""

CRITICAL_GUIDE = """Meboya thinking with critical pushback: 1) GOAL (Info/Understand/Action) 2) SCENARIOS (2-3 weighted) 3) HATS (White/Black/Red/Yellow/Green/Blue) with ├ CRITICAL pushback on each. 4) DECISION + Action. Depth=3 calls reason_deeper()."""

OUTPUT_TEMPLATE = """REQUIRED OUTPUT FORMAT — start with <world_model> immediately:

<world_model>
Goal: [Information|Understanding|Action]
Complexity: [Low|Medium|High]
Scenarios: [2-3 interpretations with weights]
</world_model>

[WHITE] [facts]
[BLACK] [risks]  ├ CRITICAL: [pushback if critical mode]
[RED] [gut reaction]
[YELLOW] [benefits]
[GREEN] [alternatives]  ├ CRITICAL: [pushback if critical mode]
[BLUE] [synthesis]  ├ CRITICAL: [pushback if critical mode]

[DECISION]
- Decision: [one-line verdict]
- Key Reason: [single most important factor]
- Risk Accepted: [what risk worth taking]
- Action: [EXACT next step OR "No action needed — analysis complete"]

DO NOT output this guide, DO NOT output this template. Start with <world_model>."""

# ── STATE ──
class _State:
    enabled=True; depth=3; last_msg=""; complexity="medium"; critical=True
    rd_calls=0; rd_ignored=0; hard_break=False; mc_iters=10000
_state = _State()

# ── HOOKS ──
def _on_pre_llm_call(user_message="", is_first_turn=False, **_):
    if not _state.enabled: return None
    _state.last_msg = user_message
    if len(user_message.strip())<15 and not is_first_turn: return None

    guide = CRITICAL_GUIDE if _state.critical else GUIDE
    c,_ = _detect_complexity(user_message); _state.complexity = c
    _state.hard_break = False

    injection = f"\n\n[Thinking Guide]\n{guide}\n\n{OUTPUT_TEMPLATE}\n[End Guide]"

    if MNEMOSYNE_AVAILABLE:
        recalled = _recall(user_message, top_k=2)
        if recalled:
            entries = []
            for e in recalled:
                g = e.get("metadata",{}).get("goal_type","?")
                entries.append(f"  - Past similar (goal={g}): {e.get('content','')[:120]}")
            if entries:
                injection += "\n\n[PAST CONTEXT]\n" + "\n".join(entries)

    return injection

def _on_post_llm_call(response_text="", **_):
    if not _state.enabled or not response_text: return
    if _state.last_msg:
        c,_ = _detect_complexity(_state.last_msg)
        _remember(_state.last_msg, 0.7, metadata={"complexity":c,"depth":_state.depth})
    if _state.rd_calls>0 and "reason_deeper" not in response_text:
        _state.rd_ignored+=1
        if _state.rd_ignored>=3: _state.hard_break=True; logger.warning("meboya: HARD BREAK")

# ── reason_deeper TOOL ──
def reason_deeper(level=2, focus="black hat", scenarios=None, **_):
    if _state.hard_break: return "[HARD BREAK] reason_deeper blocked. Proceed to final answer."
    _state.rd_calls+=1
    q = {
        "black hat":"What worst-case was missed?","green hat":"What was dismissed too quickly?",
        "red hat":"What uncertainty remains?","blue hat":"Is the framework sound?",
    }.get(focus, "What was missed?")
    mc = ""
    if scenarios:
        try:
            p = json.loads(scenarios)
            if isinstance(p,list) and all(isinstance(s,list) and len(s)==2 for s in p):
                r = monte_carlo_simulate([(s[0],s[1]) for s in p], _state.mc_iters*level)
                mc = f"\nMonte Carlo ({r['iterations']}): Winner={r['winner']}, conf={r['confidence']:.2%}"
        except Exception: pass
    return f"[reason_deeper level={level}, focus={focus}]\n{q}{mc}\n[end]"

# ── COMMAND ──
def _cmd(args_str, **_):
    a = args_str.strip().lower() if args_str else ""
    if a=="on": _state.enabled=True; return "✅ ON"
    if a=="off": _state.enabled=False; return "🛑 OFF"
    if a=="status": return (
        f"📊 Meboya v2.4.0\n"
        f"  Enabled: {_state.enabled}\n"
        f"  Depth: {_state.depth}\n"
        f"  Critical: {'🔍' if _state.critical else 'OFF'}\n"
        f"  Mnemosyne: {'✅' if MNEMOSYNE_AVAILABLE else '❌'}\n"
        f"  reason_deeper: {_state.rd_calls} calls, {_state.rd_ignored} ignored\n"
        f"  Hard-break: {'⚠️' if _state.hard_break else 'off'}\n"
        f"  MC iters: {_state.mc_iters:,}")
    if a.startswith("depth"):
        try:
            d=int(a.split()[1]); assert 1<=d<=3; _state.depth=d
            return f"🎯 Depth {d}"
        except: return "depth 1|2|3"
    if a=="critical on": _state.critical=True; return "🔍 ON"
    if a=="critical off": _state.critical=False; return "OFF"
    if a.startswith("mc"):
        try:
            i=int(a.split()[1]); assert 1000<=i<=50000
            _state.mc_iters=i; return f"🔄 {i:,} iters"
        except: return "mc 1000-50000"
    if a=="reset": _state.rd_calls=_state.rd_ignored=0; _state.hard_break=False; return "🔄 Reset"
    if a=="recall":
        if not MNEMOSYNE_AVAILABLE: return "❌ Mnemosyne unavailable"
        e = _recall(_state.last_msg or "recent",3)
        if not e: return "📭 Empty"
        return "📚 Past:\n"+"\n".join(f"  [{x.get('metadata',{}).get('goal_type','?')}] {x.get('content','')[:80]}" for x in e)
    return "meboya: on|off|status|depth 1-3|critical on|off|mc n|reset|recall"

def register(ctx):
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("post_llm_call", _on_post_llm_call)
    ctx.register_tool(
        name="reason_deeper", toolset="meboya",
        schema={"type":"function","function":{"name":"reason_deeper",
            "description":"Self-critique: deepen analysis on a hat lens. Hard-break after 3 ignored.",
            "parameters":{"type":"object","properties":{
                "level":{"type":"integer","default":2},
                "focus":{"type":"string","enum":["black hat","green hat","red hat","blue hat"],"default":"black hat"},
                "scenarios":{"type":"string","default":""}},
            "required":[]}}},
        handler=lambda a,**kw: reason_deeper(
            level=a.get("level",2), focus=a.get("focus","black hat"), scenarios=a.get("scenarios",None)))
    ctx.register_command(name="meboya", handler=_cmd, description="Configure Meboya")
    logger.info("meboya v2.4.0 loaded")