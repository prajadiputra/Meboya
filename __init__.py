"""Meboya — Balinese for "questioning everything".

Auto-thinking plugin for Hermes Agent.
Injects structured reasoning: Goal Detection + Scenario Generation + Six Thinking Hats
+ Critical Mode + Monte Carlo simulation + Recursive Reasoning (reason_deeper).
Optional Mnemosyne memory. Zero hard dependencies (stdlib Python).
"""

from __future__ import annotations

import json
import logging
import math
import random
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Optional Mnemosyne
# ──────────────────────────────────────────────────────────────────────

MNEMOSYNE_AVAILABLE = False
_mnemosyne = None

try:
    from mnemosyne import Mnemosyne
    _mnemosyne = Mnemosyne()
    MNEMOSYNE_AVAILABLE = True
    logger.info("meboya: Mnemosyne connected")
except ImportError:
    logger.debug("meboya: mnemosyne not installed (graceful fallback)")
except Exception as e:
    logger.warning("meboya: mnemosyne init failed: %s", e)


def _remember(content: str, importance: float = 0.7, source: str = "meboya",
              metadata: Optional[Dict] = None) -> Optional[str]:
    if not MNEMOSYNE_AVAILABLE or not _mnemosyne:
        return None
    try:
        kwargs: Any = {"content": content, "importance": importance, "source": source}
        if metadata:
            kwargs["metadata"] = metadata
        return _mnemosyne.remember(**kwargs)
    except Exception as e:
        logger.debug("meboya: remember failed: %s", e)
        return None


def _recall(query: str, top_k: int = 3) -> List[Dict]:
    if not MNEMOSYNE_AVAILABLE or not _mnemosyne:
        return []
    try:
        return _mnemosyne.recall(query, top_k=top_k) or []
    except Exception as e:
        logger.debug("meboya: recall failed: %s", e)
        return []


# ──────────────────────────────────────────────────────────────────────
# Goal detection
# ──────────────────────────────────────────────────────────────────────

_GOAL_RE = re.compile(
    r"<world_model>.*?(Information|Understanding|Action)",
    re.DOTALL | re.IGNORECASE,
)


def _detect_goal_type(text: str) -> str:
    m = _GOAL_RE.search(text)
    return m.group(1).lower() if m else "unknown"


def _detect_complexity(text: str) -> Tuple[str, int]:
    low = sum(kw in text.lower() for kw in (
        "simple", "trivial", "what is", "who is", "when is", "define"))
    high = sum(kw in text.lower() for kw in (
        "deploy", "architecture", "optimize", "refactor", "migrate",
        "security", "incident", "cost", "troubleshoot", "latency", "scale"))
    if high >= 2:
        return ("high", min(80 + high * 5, 99))
    if low >= 2:
        return ("low", min(20 + low * 5, 40))
    return ("medium", 50)


# ──────────────────────────────────────────────────────────────────────
# Monte Carlo — pure Python, 0 LLM tokens
# ──────────────────────────────────────────────────────────────────────

def monte_carlo_simulate(
    scenarios: List[Tuple[str, float]],
    iterations: int = 10000,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Run Monte Carlo simulation over weighted scenarios.

    scenarios: list of (label, probability_weight) tuples. Weights are
               relative — normalised to sum to 1.0 internally.
    iterations: number of simulation runs (default 10000, range 1000-50000).
    seed: optional RNG seed for reproducibility.

    Returns dict with:
      - probabilities: {label: final_probability}
      - winner: label with highest probability
      - confidence: spread between highest and second-highest
      - iterations: actual iterations run
      - raw_counts: {label: integer count}
    """
    if not scenarios:
        return {"error": "no scenarios provided", "winner": "none"}
    actual_iters = max(1000, min(iterations, 50000))
    weights = [max(s[1], 0.01) for s in scenarios]
    total_w = sum(weights)
    probs = [w / total_w for w in weights]
    labels = [s[0] for s in scenarios]

    rng = random.Random(seed) if seed else random.Random()
    counts = [0] * len(labels)
    for _ in range(actual_iters):
        r = rng.random()
        cumulative = 0.0
        for i, p in enumerate(probs):
            cumulative += p
            if r <= cumulative:
                counts[i] += 1
                break

    final_probs = [c / actual_iters for c in counts]
    indexed = sorted(enumerate(final_probs), key=lambda x: -x[1])
    winner_idx = indexed[0][0]
    spread = indexed[0][1] - (indexed[1][1] if len(indexed) > 1 else 0.0)

    return {
        "probabilities": {labels[i]: round(final_probs[i], 4) for i in range(len(labels))},
        "winner": labels[winner_idx],
        "confidence": round(spread, 4),
        "iterations": actual_iters,
        "raw_counts": {labels[i]: counts[i] for i in range(len(labels))},
    }


# ──────────────────────────────────────────────────────────────────────
# Prompt templates (COMPLIANCE FOCUSED — short, explicit)
# ──────────────────────────────────────────────────────────────────────

GOAL_DETECTION = """Before answering:
1. Identify the user's primary need: Information / Understanding / Action.
2. Generate 2-3 possible scenarios or interpretations of their request.
   For each scenario, give a probability weight (0.0-1.0).
3. Use the goal + scenarios to shape your response structure.

If depth >= 2, format scenarios in a [SCENARIOS] block in your final output.
If depth >= 3, you may call `reason_deeper` for self-critique."""

HATS_INSTRUCTION = """After scenarios, apply Six Thinking Hats in order:
[WHITE] Facts, data, constraints
[BLACK] Risks, edge cases, pitfalls
[YELLOW] Benefits, opportunities, value
[GREEN] Alternatives, creative options
[BLUE] Synthesis and recommendation

Then output a [DECISION] block at the end:
[DECISION]
- Decision: [one-line verdict]
- Key Reason: [single most important factor]
- Risk Accepted: [what risk is worth taking]
- Action: [EXACT next step OR "No action needed — analysis complete"]

If Action is a concrete step, EXECUTE IT IMMEDIATELY. Do not ask permission.

**YOUR OUTPUT MUST START WITH [SCENARIOS] or [WHITE] — no preamble, no echo of these instructions.**
Just produce the answer using the tags."""

CRITICAL_INSTRUCTION = """After scenarios, apply Six Thinking Hats with critical pushback:
[WHITE] Facts, data, constraints
[BLACK] Risks, edge cases, pitfalls
  ├ CRITICAL: [premise challenge]
  ├ CRITICAL: [hidden requirements]
  └ CRITICAL: [worst-case path]
[RED] Gut reaction
[YELLOW] Benefits, opportunities, value
[GREEN] Alternatives, creative options
  ├ CRITICAL: [opposite approach]
  └ CRITICAL: [domain expert view]
[BLUE] Synthesis and recommendation
  ├ CRITICAL: [best answer or just easiest?]
  └ CRITICAL: [second-order effects]

Then output [DECISION] block:
[DECISION]
- Decision: [one-line verdict]
- Key Reason: [single most important factor]
- Risk Accepted: [what risk is worth taking]
- Action: [EXACT next step OR "No action needed — analysis complete"]

**CRITICAL: If depth=3, call `reason_deeper` after [DECISION] to critique your own conclusion.**
**YOUR OUTPUT MUST START WITH [SCENARIOS] or [WHITE] — no preamble, no echo of instructions.**"""

LIGHT_PROMPT = GOAL_DETECTION
MEDIUM_PROMPT = f"{GOAL_DETECTION}\n\n{HATS_INSTRUCTION}"
DEEP_PROMPT = f"""{GOAL_DETECTION}

{HATS_INSTRUCTION}

After [DECISION], evaluate whether your conclusion needs deeper critique:
- If the problem is complex, call `reason_deeper(level=2, focus="black hat")`
- If confidence is low, call `reason_deeper(level=3, focus="green hat")`
- If you see strong objections you didn't address, call `reason_deeper(level=2, focus="red hat")`

reason_deeper will run additional Monte Carlo simulation and return a refined view."""

CRITICAL_LIGHT = f"{GOAL_DETECTION}\n\n{CRITICAL_INSTRUCTION}"
CRITICAL_MEDIUM = f"{GOAL_DETECTION}\n\n{CRITICAL_INSTRUCTION}"
CRITICAL_DEEP = f"""{GOAL_DETECTION}

{CRITICAL_INSTRUCTION}

After [DECISION], evaluate whether your conclusion needs deeper critique:
- If the problem is complex, call `reason_deeper(level=2, focus="black hat")`
- If confidence is low, call `reason_deeper(level=3, focus="green hat")`
- If you see strong objections you didn't address, call `reason_deeper(level=2, focus="red hat")`

reason_deeper will run additional Monte Carlo simulation and return a refined view."""

DEPTH_PROMPTS = {1: LIGHT_PROMPT, 2: MEDIUM_PROMPT, 3: DEEP_PROMPT}
CRITICAL_DEPTH_PROMPTS = {1: CRITICAL_LIGHT, 2: CRITICAL_MEDIUM, 3: CRITICAL_DEEP}


# ──────────────────────────────────────────────────────────────────────
# Plugin state
# ──────────────────────────────────────────────────────────────────────

class _State:
    enabled: bool = True
    depth: int = 3
    last_user_message: str = ""
    last_goal_type: str = "unknown"
    last_complexity: str = "medium"
    critical_mode: bool = True
    # reason_deeper tracking
    reason_deeper_calls: int = 0
    reason_deeper_ignored: int = 0
    hard_break_triggered: bool = False
    monte_carlo_default_iters: int = 10000


_state = _State()


# ──────────────────────────────────────────────────────────────────────
# Hooks
# ──────────────────────────────────────────────────────────────────────

def _on_pre_llm_call(
    user_message: str = "",
    conversation_history: list = None,
    is_first_turn: bool = False,
    **_: Any,
) -> Optional[str]:
    if not _state.enabled:
        return None

    _state.last_user_message = user_message

    if len(user_message.strip()) < 15 and not is_first_turn:
        return None

    guide = DEPTH_PROMPTS.get(_state.depth, MEDIUM_PROMPT)
    if _state.critical_mode:
        critical_level = _state.depth
        guide = CRITICAL_DEPTH_PROMPTS.get(critical_level, CRITICAL_DEPTH_PROMPTS[2])

    c_label, _ = _detect_complexity(user_message)
    _state.last_complexity = c_label

    # Build injection — short intro + guide
    injection = f"\n\n[Thinking Guide]\n{guide}\n[End Guide]"

    # Mnemosyne recall
    if MNEMOSYNE_AVAILABLE:
        recalled = _recall(user_message, top_k=2)
        if recalled:
            entries = []
            for entry in recalled:
                content = entry.get("content", "")
                goal = entry.get("metadata", {}).get("goal_type", "?")
                entries.append(f"  - Past similar query (goal={goal}): {content[:120]}")
            if entries:
                injection += (
                    "\n\n[PAST CONTEXT — these were user goals for similar past queries. "
                    "Use this to calibrate.]\n"
                    + "\n".join(entries)
                )

    # Hard-break reset per user message
    _state.hard_break_triggered = False

    logger.debug(
        "meboya: injected depth=%d chars=%d mnemosyne=%s",
        _state.depth, len(injection), MNEMOSYNE_AVAILABLE,
    )
    return injection


def _on_post_llm_call(
    response_text: str = "",
    user_message: str = "",
    **_: Any,
) -> None:
    if not _state.enabled or not response_text:
        return
    if _state.last_user_message:
        goal_type = _detect_goal_type(response_text)
        c_label, c_score = _detect_complexity(_state.last_user_message)
        _remember(
            content=_state.last_user_message,
            importance=0.7,
            source="meboya",
            metadata={
                "goal_type": goal_type,
                "complexity": c_label,
                "complexity_score": c_score,
                "depth": _state.depth,
            },
        )
        _state.last_goal_type = goal_type

    # Detect if model ignored reason_deeper (response doesn't mention it)
    if _state.reason_deeper_calls > 0 and "reason_deeper" not in response_text:
        _state.reason_deeper_ignored += 1
        logger.debug("meboya: reason_deeper ignored #%d", _state.reason_deeper_ignored)
        if _state.reason_deeper_ignored >= 3:
            _state.hard_break_triggered = True
            logger.warning("meboya: HARD BREAK — reason_deeper ignored 3 times, auto-stopped")


# ──────────────────────────────────────────────────────────────────────
# reason_deeper tool — recursive self-critique
# ──────────────────────────────────────────────────────────────────────

def reason_deeper(
    level: int = 2,
    focus: str = "black hat",
    scenarios: Optional[str] = None,
    **_: Any,
) -> str:
    """Recursive self-critique tool. Call to deepen analysis on a specific lens.

    Args:
        level: critique depth (2=medium, 3=deep)
        focus: which hat lens to focus ("black hat", "green hat", "red hat", "blue hat")
        scenarios: optional JSON list of scenarios for Monte Carlo

    Returns:
        Formatted critique text.
    """
    if _state.hard_break_triggered:
        return (
            "[reason_deeper BLOCKED: hard-break active. "
            "You have ignored reason_deeper 3 times. "
            "Proceed to final answer without further recursion.]"
        )

    _state.reason_deeper_calls += 1

    # Map hat lens to critique angle
    focus_map = {
        "black hat": "What did you miss? What worst-case scenario wasn't weighed?",
        "green hat": "What creative alternative did you dismiss too quickly?",
        "red hat": "What gut feeling did you suppress? What uncertainty remains?",
        "blue hat": "Is the decision framework itself sound? What's the meta-view?",
        "white hat": "What facts or data might be missing or outdated?",
        "yellow hat": "What upside did you undervalue?",
    }
    question = focus_map.get(focus, focus_map["black hat"])

    # Run Monte Carlo if scenarios provided
    mc_result = ""
    if scenarios:
        try:
            parsed = json.loads(scenarios)
            if isinstance(parsed, list) and all(isinstance(s, list) and len(s) == 2 for s in parsed):
                sim_result = monte_carlo_simulate(
                    [(s[0], s[1]) for s in parsed],
                    iterations=_state.monte_carlo_default_iters * level,
                )
                mc_result = f"\n\nMonte Carlo ({sim_result['iterations']} iters):\n"
                for label, prob in sorted(
                    sim_result["probabilities"].items(), key=lambda x: -x[1]
                ):
                    mc_result += f"  {label}: {prob*100:.1f}%\n"
                mc_result += f"Winner: {sim_result['winner']} (confidence: {sim_result['confidence']*100:.1f}%)"
        except (json.JSONDecodeError, TypeError):
            mc_result = "\n\n(Monte Carlo simulation not run — invalid scenario format)"

    return (
        f"[reason_deeper level={level}, focus={focus}]\n"
        f"Critique: {question}\n"
        f"{mc_result}\n"
        f"[end reason_deeper]"
    )


# ──────────────────────────────────────────────────────────────────────
# /meboya command
# ──────────────────────────────────────────────────────────────────────

def _cmd_meboya(args: str, **_: Any) -> str:
    a = (args or "").strip().lower()

    if a == "on":
        _state.enabled = True
        return "✅ Meboya ENABLED"
    if a == "off":
        _state.enabled = False
        return "🛑 Meboya DISABLED"
    if a == "status":
        return (
            f"📊 Meboya status:\n"
            f"  Enabled: {_state.enabled}\n"
            f"  Depth: {_state.depth} (1-3)\n"
            f"  Critical mode: {'🔍 ON' if _state.critical_mode else 'OFF'}\n"
            f"  Mnemosyne: {'✅ connected' if MNEMOSYNE_AVAILABLE else '❌ unavailable'}\n"
            f"  Last complexity: {_state.last_complexity}\n"
            f"  reason_deeper calls: {_state.reason_deeper_calls}\n"
            f"  reason_deeper ignored: {_state.reason_deeper_ignored}\n"
            f"  Hard-break: {'⚠️ ACTIVE' if _state.hard_break_triggered else 'off'}\n"
            f"  Monte Carlo default iters: {_state.monte_carlo_default_iters:,}"
        )
    if a.startswith("depth"):
        try:
            d = int(a.split()[1])
            if 1 <= d <= 3:
                _state.depth = d
                return f"🎯 Depth set to {d}"
        except (IndexError, ValueError):
            pass
        return "Usage: /meboya depth 1|2|3"
    if a == "critical on":
        _state.critical_mode = True
        return "🔍 Critical analysis mode ON"
    if a == "critical off":
        _state.critical_mode = False
        return "🔍 Critical analysis mode OFF"
    if a.startswith("mc"):
        parts = a.split()
        if len(parts) == 2:
            try:
                iters = int(parts[1])
                if 1000 <= iters <= 50000:
                    _state.monte_carlo_default_iters = iters
                    return f"🔄 Monte Carlo default iterations set to {iters:,}"
            except ValueError:
                pass
        return "Usage: /meboya mc <iterations> (1000-50000)"
    if a == "reset":
        _state.reason_deeper_calls = 0
        _state.reason_deeper_ignored = 0
        _state.hard_break_triggered = False
        return "🔄 reason_deeper counters reset"
    if a == "recall":
        if not MNEMOSYNE_AVAILABLE:
            return "❌ Mnemosyne not available"
        entries = _recall(_state.last_user_message or "recent", top_k=3)
        if not entries:
            return "📭 No past memory found"
        lines = ["📚 Past thought patterns:"]
        for e in entries:
            c = e.get("content", "")[:100]
            g = e.get("metadata", {}).get("goal_type", "?")
            lines.append(f"  [{g}] {c}")
        return "\n".join(lines)

    return (
        "Usage: /meboya [on|off|status|depth 1-3|critical on|off|mc <iters>|reset|recall]\n"
        "  depth 1 = goal + scenarios\n"
        "  depth 2 = + hats + decision\n"
        "  depth 3 = + reason_deeper self-critique\n"
        "  critical on|off = toggle adversarial pushback\n"
        "  mc <iters> = set Monte Carlo default iterations\n"
        "  reset = reset reason_deeper counters\n"
        "  recall = show past patterns from Mnemosyne"
    )


# ──────────────────────────────────────────────────────────────────────
# Hermes entry point
# ──────────────────────────────────────────────────────────────────────

def register(ctx):
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("post_llm_call", _on_post_llm_call)
    ctx.register_tool(
        name="reason_deeper",
        toolset="meboya",
        schema={
            "type": "function",
            "function": {
                "name": "reason_deeper",
                "description": "Recursive self-critique. Deepens analysis on a specific hat lens. "
                               "Use when analysis feels incomplete or confidence is low. "
                               "HARD-BREAK: after 3 ignored calls, tool auto-blocks.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "level": {
                            "type": "integer",
                            "description": "Critique depth: 2=medium, 3=deep",
                            "default": 2,
                        },
                        "focus": {
                            "type": "string",
                            "enum": ["black hat", "green hat", "red hat", "blue hat",
                                     "white hat", "yellow hat"],
                            "description": "Which hat lens to critique",
                            "default": "black hat",
                        },
                        "scenarios": {
                            "type": "string",
                            "description": "Optional JSON: [[label, prob], ...] for Monte Carlo",
                            "default": "",
                        },
                    },
                    "required": [],
                },
            },
        },
        handler=lambda args, **kw: reason_deeper(
            level=args.get("level", 2),
            focus=args.get("focus", "black hat"),
            scenarios=args.get("scenarios", None),
        ),
        requires_env=[],
    )
    ctx.register_command(
        name="meboya",
        handler=_cmd_meboya,
        description="Configure Meboya (on/off/status/depth/critical/mc/reset/recall)",
        args_hint="[on|off|status|depth 1-3|critical on|off|mc <iters>|reset|recall]",
    )
    logger.info(
        "meboya plugin registered (depth=%d, critical=%s, mnemosyne=%s, reason_deeper+mc=loaded)",
        _state.depth, _state.critical_mode, MNEMOSYNE_AVAILABLE,
    )