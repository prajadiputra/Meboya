"""Meboya — questioning everything. Thinking layer for Hermes Agent."""
from __future__ import annotations
import json, logging, os, random, re
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

# ── GUARDRAIL: fact verification discipline ──
VERIFY_RULE = ("CRITICAL RULE: NO ASSUMPTIONS. Every [WHITE] fact MUST be supported by "
               "verified data: documentation, tool output, DB query, or direct observation. "
               "NEVER infer meaning of prefixes/names/terms from pattern-matching or memory. "
               "If uncertain, state '🔍 unknown — needs verification' — do not guess.")

# ── INSTRUCTION (DOGA-style) ──
INSTRUCTION = ("Put [WHITE] facts, [BLACK] risks, [YELLOW] benefits, [GREEN] alternatives, "
               "and [BLUE] synthesis inside <world_model>...</world_model>, then output:\n"
               "[DECISION]\n- Decision:\n- Key Reason:\n- Risk Accepted:\n- Action:\n"
               "After [DECISION], ask one natural follow-up question.\n\n"
               f"{VERIFY_RULE}")

CRITICAL_INSTRUCTION = ("Put [WHITE] facts (VERIFIED ONLY — see rule below), [BLACK] risks with ├ CRITICAL: pushback, "
                        "[RED] gut reaction, "
                        "[YELLOW] benefits, [GREEN] alternatives with ├ CRITICAL: pushback, and [BLUE] synthesis "
                        "with ├ CRITICAL: pushback inside <world_model>...</world_model>, then output:\n"
                        "[DECISION]\n- Decision:\n- Key Reason:\n- Risk Accepted:\n- Action:\n"
                        "After [DECISION], ask one natural follow-up question.\n\n"
                        f"{VERIFY_RULE}")

# ── SOCRATIC ENHANCEMENT (core question bank, deterministic injection) ──
# Self-contained: question files ship inside plugin at socratic/questions/core/.
# Unlike Socratic SKILL.md, no LLM tool-load round-trip required.
SOCRATIC_DIR = os.path.join(os.path.dirname(__file__), "socratic", "questions", "core")
SOCRATIC_ENABLED = True
# signal word -> domain file (mirrors upstream SKILL.md signal table). "or" = any word.
SOCRATIC_DOMAINS = [
    ("ui|page|component|dashboard|form|frontend",        "01-frontend"),
    ("service|endpoint|job|queue|backend|business logic", "02-backend"),
    ("database|schema|storage|persistence|migration|cache","03-data"),
    ("api|sdk|webhook|connector|integration|oauth",       "04-api"),
    ("authentication|auth|accounts|payments|secrets|public",   "05-security"),
    ("deploy|ci/cd|container|cloud|scaling|kubernetes|k8s|istio|httproute|eks|cluster|vpc|helm", "06-infra"),
    ("production|unattended|cron|monitor|observability|rollback","08-observability"),
    ("ai|llm|agent|prompt|model|rag",                     "09-ai-llm"),
    ("mobile|ios|android|offline|pwa",                    "10-mobile"),
    ("workflow|onboarding|cli|ux",                        "11-product-ux"),
    ("scale|latency|traffic|cost|token",                  "12-cost-performance"),
    ("regulated|pii|health|finance|minors|license",       "13-compliance"),
    ("maintained|long-lived|team|legacy",                 "14-team-maintenance"),
]
# trigger words = request signals a build/design/review task (vs plain chat)
SOCRATIC_TRIGGERS = ("build", "design", "scaffold", "architect", "plan", "create",
                     "implement", "migrate", "migration", "migrasi", "review", "poke holes",
                     "what am i missing", "what is missing", "bikin", "bangun",
                     "buatkan", "convert", "apa yang perlu", "apa saja yang perlu",
                     "tinjau", "audit", "rencana")
SOCRATIC_BASE = ("00-requirements", "07-testing")  # always included

_socratic_cache = {}

def _socratic_read(dom):
    """Read a core question file (cached); return '' if missing/failed."""
    key = (SOCRATIC_DIR, dom)  # cache key includes dir — survives dir swap in tests
    if key in _socratic_cache:
        return _socratic_cache[key]
    try:
        with open(os.path.join(SOCRATIC_DIR, dom + ".md"), encoding="utf-8") as f:
            content = f.read()
        _socratic_cache[key] = content
        return content
    except Exception as e:
        logger.debug("socratic read %s:%s", dom, e)
        _socratic_cache[key] = ""
        return ""

def _word_in(text, word):
    """Word-boundary match: 'plan' not in 'explanation'; 'ui' not in 'quick'."""
    return re.search(r"(?<![a-z0-9])" + re.escape(word.lower()) + r"(?![a-z0-9])", text) is not None

def _socratic_injection(msg):
    if not SOCRATIC_ENABLED or not msg:
        return None
    m = msg.lower()
    if not any(_word_in(m, t) for t in SOCRATIC_TRIGGERS):
        return None
    doms = list(SOCRATIC_BASE)
    for sig, dom in SOCRATIC_DOMAINS:
        if any(_word_in(m, w) for w in sig.split("|") if w.strip()):
            doms.append(dom)
    body = "\n\n".join(x for x in (_socratic_read(d) for d in dict.fromkeys(doms)) if x)
    if not body:
        return None
    return ("\n\n---MEBOYA/SOCRATIC: A build/design task detected. Self-answer these "
            "engineering questions (loaded for you, no tool call needed), then fold the "
            "answers into your decision. Do not output raw questions. Cover, per domain: "
            "requirements, assumptions (flag defaults), material risks, and how you will "
            "verify. "
            "MANDATORY — you MUST write the contract below INSIDE <world_model>, after the "
            "hat panel and BEFORE [DECISION]. It is required output, not optional. Keep it "
            "compact — exact labels, one dense line each, no prose:\n"
            "- Domains considered: <comma-separated>\n"
            "- Self-answered: <what you resolved yourself>\n"
            "- Assumed (flag if wrong): <defaults you assumed — flag explicitly>\n"
            "- Open questions for you (0-3): <what still needs the user>\n"
            "- Top risks: <top 2-3>\n"
            "- Plan: <next step>\n"
            "If you skip the contract, you fail the task. Domain files loaded:\n" +
            "\n".join("- " + d for d in doms) + "\n\n" + body)

# ── STATE ──
class _State:
    enabled=True; depth=3; last_msg=""; complexity="medium"; critical=True
    hats_enabled=True; auto_depth=True; max_recursion=3; show_mode=True
    rd_calls=0; rd_ignored=0; hard_break=False; mc_iters=10000
    soc_triggered=0; soc_contract=0; soc_tokens_in=0
_state = _State()

# ── HOOKS ──
def _format_show_hide(response_text=""):
    """DOGA-style: strip thinking panel when hide; keep [DECISION] + follow-up.

    Primary path: strip closed <world_model>...</world_model>.
    Fallback: if model emits [WHITE]...[BLUE] outside tags, keep from [DECISION] onward;
    if [DECISION] is missing entirely, drop the hat block and keep trailing text.
    """
    if not response_text or _state.show_mode:
        return response_text
    import re
    cleaned = re.sub(r"<world_model>.*?</world_model>", "", response_text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"</?world_model>\s*", "", cleaned, flags=re.IGNORECASE).strip()
    hat_tags = ("[WHITE]", "[BLACK]", "[RED]", "[YELLOW]", "[GREEN]", "[BLUE]")
    if any(t in cleaned for t in hat_tags):
        m = re.search(r"(?m)^\[DECISION\]", cleaned)
        if m:
            cleaned = cleaned[m.start():].strip()
        else:
            # no DECISION marker — drop the hat block (up to the last hat line),
            # keep whatever follows (conclusion / follow-up)
            lines = cleaned.splitlines()
            last_hat = -1
            for i, ln in enumerate(lines):
                if any(ln.lstrip().startswith(t) for t in hat_tags) or ln.lstrip().startswith("├ CRITICAL"):
                    last_hat = i
            if last_hat >= 0:
                cleaned = "\n".join(lines[last_hat + 1:]).strip()
    return cleaned or response_text


def _on_pre_llm_call(user_message="", is_first_turn=False, **_):
    if not _state.enabled: return None
    _state.last_msg = user_message
    if len(user_message.strip()) < 5 and not is_first_turn: return None
    # Depth-gated guide selection (fix: depth was ignored)
    depth = _state.depth
    if not _state.hats_enabled or depth < 2:
        guide = ("Put concise analysis inside <world_model>...</world_model>, then output:\n"
                 "[DECISION]\n- Decision:\n- Key Reason:\n- Risk Accepted:\n- Action:\n"
                 "Ask one natural follow-up question after [DECISION].")
    else:
        guide = CRITICAL_INSTRUCTION if _state.critical else INSTRUCTION
    c,_ = _detect_complexity(user_message); _state.complexity = c
    _state.hard_break = False
    injection = f"\n\n---MEBOYA: {guide}"
    # depth >= 3: hint model may use reason_deeper tool
    if depth >= 3:
        injection += ("\n(You have the reason_deeper tool available — use it for self-critique "
                      "when the decision carries real risk.)")
    # Mnemosyne recall goes to system context, NOT user message injection
    # (prevents PAST: text leaking into [DECISION] Action field)
    soc = _socratic_injection(user_message)
    if soc:
        injection += soc
    return injection

def _on_post_llm_call(response_text="", **_):
    if not _state.enabled: return
    if _state.last_msg:
        c,_=_detect_complexity(_state.last_msg)
        _remember(_state.last_msg,0.7,md={"complexity":c,"depth":_state.depth})
        # ── SOCRATIC effectiveness telemetry ──
        injected = bool(_socratic_injection(_state.last_msg))
        if injected:
            _state.soc_triggered += 1
            contract_out = any(k in (response_text or "") for k in
                               ("Domains considered", "Self-answered", "Assumed (flag if wrong)",
                                "Open questions", "Top risks", "Plan:"))
            _state.soc_contract += 1 if contract_out else 0
            _state.soc_tokens_in += len(_socratic_injection(_state.last_msg)) // 4
            logger.info("socratic: triggered=%s contract=%s", _state.soc_triggered, contract_out)
    # Hard-break: track ONLY consecutive turns where reason_deeper was available
    # and the model chose not to call it. Reset per-turn when it IS called.
    if _state.rd_calls > 0 and response_text:
        if "reason_deeper" in response_text:
            _state.rd_ignored = 0  # tool was used — reset streak
        else:
            _state.rd_ignored += 1
            if _state.rd_ignored >= 3:
                _state.hard_break = True
                logger.warning("meboya: HARD BREAK")

def _on_transform_llm_output(response_text="", **_):
    """DOGA-style: strip <world_model> when hide; reasoning stays intact upstream."""
    return _format_show_hide(response_text)

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
    global SOCRATIC_ENABLED
    a=a.strip().lower() if a else ""
    if a=="on": _state.enabled=True; return "ON"
    if a=="off": _state.enabled=False; return "OFF"
    if a=="status":
        mode = "auto" if _state.auto_depth else "manual"
        return (f"Meboya v2.7.4\n"
                f"  Enabled: {_state.enabled}\n"
                f"  Mode: {mode}\n"
                f"  Depth: {_state.depth} (1=concise, 2=hats, 3=hats+reason_deeper)\n"
                f"  Hats: {'ON' if _state.hats_enabled else 'OFF'}\n"
                f"  Show: {'ON' if _state.show_mode else 'OFF (panel hidden)'}\n"
                f"  Critical: {'ON' if _state.critical else 'OFF'}\n"
                f"  Mnemosyne: {'Y' if MNEMOSYNE_AVAILABLE else 'N'}\n"
                f"  MC iters: {_state.mc_iters:,}\n"
                f"  Max recursion: {_state.max_recursion}\n"
                f"  reason_deeper: {_state.rd_calls} calls, {_state.rd_ignored} ignored\n"
                f"  Hard-break: {'ON' if _state.hard_break else 'OFF'}\n"
                f"  Socratic: {'ON' if SOCRATIC_ENABLED else 'OFF'}\n"
                f"    triggered: {_state.soc_triggered} turns\n"
                f"    contract emitted: {_state.soc_contract}/{_state.soc_triggered} ({(_state.soc_contract*100//_state.soc_triggered) if _state.soc_triggered else 0}%)\n"
                f"    tokens injected: ~{_state.soc_tokens_in:,}")
    if a=="auto": _state.auto_depth=True; return "auto (depth auto-selected per query)"
    if a.startswith("manual"):
        try:
            lvl=a.split()[1].lower()
            m={"low":1,"medium":2,"high":3}
            if lvl in m: _state.auto_depth=False; _state.depth=m[lvl]; return f"manual {lvl} (depth={m[lvl]})"
        except: pass
        return "manual low|medium|high"
    if a.startswith("depth"):
        try: d=int(a.split()[1]); assert 1<=d<=3; _state.depth=d; _state.auto_depth=False; return f"depth {d}"
        except: return "depth 1|2|3"
    if a=="hats on": _state.hats_enabled=True; return "hats ON"
    if a=="hats off": _state.hats_enabled=False; return "hats OFF"
    if a=="show": _state.show_mode=True; return "show (simulation panel ON)"
    if a=="hide": _state.show_mode=False; return "hide (simulation panel OFF)"
    if a=="critical on": _state.critical=True; return "critical ON"
    if a=="critical off": _state.critical=False; return "critical OFF"
    if a=="hard-break on": _state.hard_break=True; return "hard-break ON"
    if a=="hard-break off": _state.hard_break=False; return "hard-break OFF"
    if a.startswith("max_recursion"):
        try: r=int(a.split()[1]); assert 1<=r<=5; _state.max_recursion=r; return f"max_recursion {r}"
        except: return "max_recursion 1-5"
    if a.startswith("mc"):
        try: i=int(a.split()[1]); assert 1000<=i<=50000; _state.mc_iters=i; return f"mc {i}"
        except: return "mc 1000-50000"
    if a.startswith("socratic"):
        if a == "socratic on": SOCRATIC_ENABLED = True; return "Socratic ON"
        if a == "socratic off": SOCRATIC_ENABLED = False; return "Socratic OFF"
        if a == "socratic":
            return ("Socratic enhancement: on|off  "
                    f"(currently {'ON' if SOCRATIC_ENABLED else 'OFF'})")
        return "socratic: on|off"
    if a=="memory on": return "memory: controlled via config.yaml"
    if a=="memory off": return "memory: disabled via config.yaml"
    if a=="reset": _state.rd_calls=_state.rd_ignored=0; _state.hard_break=False; return "reset"
    if a=="recall":
        if not MNEMOSYNE_AVAILABLE: return "No Mnemosyne"
        e=_recall(_state.last_msg or "recent",3)
        return "Past:\n"+"\n".join(f"[{x.get('metadata',{}).get('goal_type','?')}] {x.get('content','')[:80]}" for x in e) if e else "empty"
    return "meboya: on|off|status|auto|manual|depth|hats|show|hide|critical|memory|max_recursion|mc|socratic|hard-break|reset|recall"

def register(ctx):
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("post_llm_call", _on_post_llm_call)
    ctx.register_hook("transform_llm_output", _on_transform_llm_output)
    ctx.register_tool(
        name="reason_deeper", toolset="meboya",
        schema={"name":"reason_deeper",
            "description":"Self-critique with hat lens. Hard-break after 3 ignored.",
            "parameters":{"type":"object","properties":{
                "level":{"type":"integer","default":2},
                "focus":{"type":"string","enum":["black hat","green hat","red hat","blue hat"],"default":"black hat"},
                "scenarios":{"type":"string","default":""}},
            "required":[]}},
        handler=lambda a,**kw: reason_deeper(
            level=a.get("level",2), focus=a.get("focus","black hat"),
            scenarios=a.get("scenarios",None)))
    ctx.register_command(name="meboya", handler=_cmd, description="Configure Meboya")
    logger.info("meboya v2.7.4 loaded (DOGA-style + socratic enhancement)")