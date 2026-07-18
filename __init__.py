"""Meboya — questioning everything. Thinking layer for Hermes Agent."""
from __future__ import annotations
import json, logging, random
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MNEMOSYNE_AVAILABLE = False; _mnemosyne = None
try:
    from mnemosyne import Mnemosyne
    _mnemosyne = Mnemosyne(); MNEMOSYNE_AVAILABLE = True
    logger.info("meboya: Mnemosyne connected")
except Exception:
    pass

def _remember(c, im=0.7, s="meboya", md=None):
    if not MNEMOSYNE_AVAILABLE: return None
    try: return _mnemosyne.remember(content=c, importance=im, source=s, metadata=md or {})
    except Exception as e: logger.debug("meboya: remember:%s",e); return None

def _recall(q, k=3):
    if not MNEMOSYNE_AVAILABLE: return []
    try: return _mnemosyne.recall(q, top_k=k) or []
    except Exception: return []

def _detect_complexity(t):
    l=sum(k in t.lower() for k in("simple","trivial","what is","who is","define"))
    h=sum(k in t.lower() for k in("deploy","architecture","migrate","security","cost","scale"))
    if h>=2: return ("high",min(80+h*5,99))
    if l>=2: return ("low",min(20+l*5,40))
    return ("medium",50)

def monte_carlo_simulate(scenarios, iterations=10000, seed=None):
    if not scenarios: return {"winner":"none","error":"no scenarios"}
    iters=max(1000,min(iterations,50000)); lbs=[s[0] for s in scenarios]
    wts=[max(s[1],0.01) for s in scenarios]; probs=[w/sum(wts) for w in wts]
    rng=random.Random(seed) if seed else random.Random()
    cnt=[0]*len(lbs)
    for _ in range(iters):
        v=rng.random(); a=0.0; hit=False
        for x,p in enumerate(probs):
            a+=p
            if v<=a:
                cnt[x]+=1; hit=True; break
        if not hit: cnt[-1]+=1
    fin=[c/iters for c in cnt]
    idx=sorted(enumerate(fin),key=lambda x:-x[1])
    return {"probabilities":{lbs[i]:round(fin[i],4) for i in range(len(lbs))},
            "winner":lbs[idx[0][0]],"confidence":round(idx[0][1]-(idx[1][1] if len(idx)>1 else 0),4),
            "iterations":iters}

# ── INSTRUCTION (DOGA-style: 1 line, model will NOT echo) ──
INSTRUCTION = ("Use <world_model> for internal reasoning, then answer with format:\n"
               "[WHITE] facts\n[BLACK] risks\n[YELLOW] benefits\n[GREEN] alternatives\n[BLUE] synthesis\n"
               "[DECISION]\n- Decision:\n- Key Reason:\n- Risk Accepted:\n- Action:")

CRITICAL_INSTRUCTION = ("Use <world_model> for internal reasoning with critical pushback, "
                        "then answer with format:\n"
                        "[WHITE] facts\n[BLACK] risks\n  ├ CRITICAL: ...\n[RED] gut reaction\n"
                        "[YELLOW] benefits\n[GREEN] alternatives\n  ├ CRITICAL: ...\n"
                        "[BLUE] synthesis\n  ├ CRITICAL: ...\n"
                        "[DECISION]\n- Decision:\n- Key Reason:\n- Risk Accepted:\n- Action:")

# ── STATE ──
class _State:
    enabled=True; depth=3; last_msg=""; complexity="medium"; critical=True
    rd_calls=0; rd_ignored=0; hard_break=False; mc_iters=10000
_state = _State()

# ── HOOKS ──
def _on_pre_llm_call(user_message="", is_first_turn=False, **_):
    if not _state.enabled: return None
    _state.last_msg = user_message
    if len(user_message.strip()) < 5 and not is_first_turn: return None
    guide = CRITICAL_INSTRUCTION if _state.critical else INSTRUCTION
    c,_ = _detect_complexity(user_message); _state.complexity = c
    _state.hard_break = False
    injection = f"\n\n---MEBOYA: {guide}"
    if MNEMOSYNE_AVAILABLE:
        recalled = _recall(user_message, k=2)
        if recalled:
            entries=[f"[{e.get('metadata',{}).get('goal_type','?')}] {e.get('content','')[:80]}" for e in recalled]
            if entries: injection += " PAST: "+"; ".join(entries)
    return injection

def _on_post_llm_call(response_text="", **_):
    if not _state.enabled or not response_text: return
    if _state.last_msg:
        c,_=_detect_complexity(_state.last_msg)
        _remember(_state.last_msg,0.7,md={"complexity":c,"depth":_state.depth})
    if _state.rd_calls>0 and "reason_deeper" not in response_text:
        _state.rd_ignored+=1
        if _state.rd_ignored>=3: _state.hard_break=True; logger.warning("meboya: HARD BREAK")

# ── reason_deeper ──
def reason_deeper(level=2, focus="black hat", scenarios=None, **_):
    if _state.hard_break: return "[HARD BREAK] reason_deeper blocked."
    _state.rd_calls+=1
    q={"black hat":"Worst-case missed?","green hat":"What dismissed too quickly?",
       "red hat":"Gut reservation?","blue hat":"Framework sound?"}.get(focus,"What missed?")
    mc=""
    if scenarios:
        try:
            p=json.loads(scenarios)
            if isinstance(p,list) and all(isinstance(s,list) and len(s)==2 for s in p):
                r=monte_carlo_simulate([(s[0],s[1]) for s in p],_state.mc_iters*level)
                mc=f"\nMC({r['iterations']}): Winner={r['winner']}, conf={r['confidence']:.1%}"
        except Exception: pass
    return f"[reason_deeper {focus}]\n{q}{mc}\n[end]"

# ── COMMAND ──
def _cmd(a="", **_):
    a=a.strip().lower() if a else ""
    if a=="on": _state.enabled=True; return "ON"
    if a=="off": _state.enabled=False; return "OFF"
    if a=="status":
        return (f"Meboya v2.5.3\n"
                f"  Enabled: {_state.enabled}\n"
                f"  Depth: {_state.depth} (1=goal, 2=hats, 3=deep+reason_deeper)\n"
                f"  Critical: {'ON' if _state.critical else 'OFF'}\n"
                f"  Mnemosyne: {'Y' if MNEMOSYNE_AVAILABLE else 'N'}\n"
                f"  reason_deeper: {_state.rd_calls} calls, {_state.rd_ignored} ignored\n"
                f"  Hard-break: {'ON' if _state.hard_break else 'OFF'}\n"
                f"  MC iters: {_state.mc_iters:,}")
    if a.startswith("depth"):
        try: d=int(a.split()[1]); assert 1<=d<=3; _state.depth=d; return f"depth {d}"
        except: return "depth 1|2|3"
    if a=="critical on": _state.critical=True; return "ON"
    if a=="critical off": _state.critical=False; return "OFF"
    if a.startswith("mc"):
        try: i=int(a.split()[1]); assert 1000<=i<=50000; _state.mc_iters=i; return f"mc {i}"
        except: return "mc 1000-50000"
    if a=="reset": _state.rd_calls=_state.rd_ignored=0; _state.hard_break=False; return "reset"
    if a=="recall":
        if not MNEMOSYNE_AVAILABLE: return "No Mnemosyne"
        e=_recall(_state.last_msg or "recent",3)
        return "Past:\n"+"\n".join(f"[{x.get('metadata',{}).get('goal_type','?')}] {x.get('content','')[:80]}" for x in e) if e else "empty"
    return "meboya: on|off|status|depth|critical|mc|reset|recall"

def register(ctx):
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("post_llm_call", _on_post_llm_call)
    ctx.register_tool(
        name="reason_deeper", toolset="meboya",
        schema={"type":"function","function":{"name":"reason_deeper",
            "description":"Self-critique with hat lens. Hard-break after 3 ignored.",
            "parameters":{"type":"object","properties":{
                "level":{"type":"integer","default":2},
                "focus":{"type":"string","enum":["black hat","green hat","red hat","blue hat"],"default":"black hat"},
                "scenarios":{"type":"string","default":""}},
            "required":[]}}},
        handler=lambda a,**kw: reason_deeper(
            level=a.get("level",2), focus=a.get("focus","black hat"),
            scenarios=a.get("scenarios",None)))
    ctx.register_command(name="meboya", handler=_cmd, description="Configure Meboya")
    logger.info("meboya v2.5.3 loaded (DOGA-style)")