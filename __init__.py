"""Meboya — Balinese for "questioning everything".

An auto-thinking plugin for Hermes Agent that injects structured prompts
(Goal Detection + Six Thinking Hats + Critical Mode) before each LLM call,
with optional Mnemosyne memory recall and write. Zero hard dependencies.

Hooks:
  pre_llm_call            → inject thinking guide (no visible wrapper)
  post_llm_call           → save goal pattern to Mnemosyne
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Optional Mnemosyne (silent fallback if missing)
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
        kwargs = {"content": content, "importance": importance, "source": source}
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
        "simple", "trivial", "what is", "who is", "when is", "define",
        "ls ", "cat ", "find ", "grep "))
    high = sum(kw in text.lower() for kw in (
        "deploy", "architecture", "optimize", "refactor", "migrate",
        "security", "incident", "cost", "troubleshoot", "latency", "scale"))
    if high >= 2:
        return ("high", min(80 + high * 5, 99))
    if low >= 2:
        return ("low", min(20 + low * 5, 40))
    return ("medium", 50)


# ──────────────────────────────────────────────────────────────────────
# Prompt templates
# ──────────────────────────────────────────────────────────────────────

GOAL_DETECTION = """Before answering, briefly identify what the user's primary need is:

- **Information**: They want factual data, analysis, or explanation.
- **Understanding**: They want to feel heard, validated, or understood.
- **Action**: They want a decision, recommendation, or next step.

Choose the dominant goal and let it shape your response."""

# ONE-SHOT: model compliance naik drastis dengan contoh eksplisit
HATS_PROMPT = """Structure your answer with mandatory hat tags for each section.

Use `<world_model>` for internal reasoning, then output your answer with:

[WHITE] Facts, data, constraints
[BLACK] Risks, edge cases, pitfalls
[YELLOW] Benefits, opportunities, value
[GREEN] Alternatives, creative options
[BLUE] Synthesis, decision, next steps

**Example output format:**
[WHITE] The request involves migrating from shared state Redis/SQL to EDA in EKS. Key factors: high-concurrency environment, existing Redis/SQL bottleneck.
[BLACK] Eventual consistency introduces complexity. Rollback strategy must be redesigned. Consumer lag in high-concurrency can cause data staleness.
[YELLOW] Decoupling enables independent scaling per service. NATS/Kafka throughput exceeds shared DB by 10-100x.
[GREEN] Alternative: keep Redis for caching + SQL for events with Debezium CDC as stepping stone before full EDA.
[BLUE] Recommended: start with NATS JetStream via Helm + outbox pattern. Roll out per-service, not big-bang.

**MANDATORY: After [BLUE], output a [DECISION] block that DECLARES the action and THEN EXECUTES it.**

[DECISION]
- **Decision:** [one-line verdict — the chosen strategy]
- **Key Reason:** [single most important factor]
- **Risk Accepted:** [what risk is worth taking]
- **Action:** [EXACT next step the agent will take NOW — a command, file edit, or delegation. If this is informational, state "No action needed — analysis complete."]

After [DECISION], if Action is a concrete step, EXECUTE IT IMMEDIATELY using available tools. Do not ask permission. If the user's request was informational only, end with the analysis."""

# Critical mode — adversarial pushback
CRITICAL_HATS_PROMPT = """Structure your answer with mandatory hat tags for each section.

Use `<world_model>` for internal reasoning, then output your answer with:

[WHITE] Facts, data, constraints
[BLACK] Risks, edge cases, pitfalls
   ├ CRITICAL: Is the premise itself valid? What assumptions may be wrong?
   ├ CRITICAL: What is the user NOT saying? Hidden requirements, unspoken constraints?
   └ CRITICAL: If this approach fails, what is the worst-case path?
[RED] Gut reaction, intuition
[YELLOW] Benefits, opportunities, value
[GREEN] Alternatives, creative options
   ├ CRITICAL: What is the OPPOSITE approach? Argue against the default.
   └ CRITICAL: What would a domain expert do differently?
[BLUE] Synthesis, decision, next steps
   ├ CRITICAL: Is this the BEST answer, or just the easiest acceptable one?
   ├ CRITICAL: Are second-order effects accounted for?
   └ CRITICAL: If challenged on this conclusion, can it be defended?

**Example output format:**
[WHITE] The request involves migrating from shared state Redis/SQL to EDA in EKS. Key factors: high-concurrency environment, existing Redis/SQL bottleneck.
[BLACK] Eventual consistency introduces complexity. Rollback strategy must be redesigned.
  ├ CRITICAL: Is the "high concurrency" requirement quantified? What QPS are we talking about?
[YELLOW] Decoupling enables independent scaling per service. NATS/Kafka throughput exceeds shared DB by 10-100x.
[GREEN] Alternative: keep Redis for caching + SQL for events with Debezium CDC as stepping stone before full EDA.
  ├ CRITICAL: What would a SRE with 10 years EKS experience do? Keep Redis as hot cache + async event fan-out.
[BLUE] Recommended: start with NATS JetStream via Helm + outbox pattern. Roll out per-service, not big-bang.
  ├ CRITICAL: Is this the BEST answer? NATS is simpler than Kafka for 10k msg/s, but if traffic spikes to 100k+ Kafka is future-proof.

**MANDATORY: After [BLUE], output a [DECISION] block that DECLARES the action and THEN EXECUTES it.**

[DECISION]
- **Decision:** [one-line verdict — the chosen strategy]
- **Key Reason:** [single most important factor]
- **Risk Accepted:** [what risk is worth taking]
- **Action:** [EXACT next step the agent will take NOW — a command, file edit, or delegation. If this is informational, state "No action needed — analysis complete."]

After [DECISION], if Action is a concrete step, EXECUTE IT IMMEDIATELY using available tools. Do not ask permission. If the user's request was informational only, end with the analysis.

Push back on the premise when warranted. Surface the dissenter view."""

LIGHT_PROMPT = GOAL_DETECTION
MEDIUM_PROMPT = f"{GOAL_DETECTION}\n\n{HATS_PROMPT}"
DEEP_PROMPT = f"""{GOAL_DETECTION}

{HATS_PROMPT}"""

CRITICAL_DEPTH_PROMPTS = {
    1: GOAL_DETECTION,
    2: f"{GOAL_DETECTION}\n\n{CRITICAL_HATS_PROMPT}",
    3: f"""{GOAL_DETECTION}

{CRITICAL_HATS_PROMPT}""",
}

DEPTH_PROMPTS = {1: LIGHT_PROMPT, 2: MEDIUM_PROMPT, 3: DEEP_PROMPT}


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
    """Inject the Meboya thinking guide before the LLM sees the prompt.
    
    NO visible wrapper markers — guide content injects directly.
    """
    if not _state.enabled:
        return None

    _state.last_user_message = user_message

    if len(user_message.strip()) < 15 and not is_first_turn:
        return None

    guide = DEPTH_PROMPTS.get(_state.depth, MEDIUM_PROMPT)
    if _state.critical_mode:
        critical_level = _state.depth
        guide = CRITICAL_DEPTH_PROMPTS.get(critical_level, CRITICAL_DEPTH_PROMPTS[2])

    c_label, c_score = _detect_complexity(user_message)
    _state.last_complexity = c_label

    # Build injection — guide only, no wrappers
    injection = f"\n\n{guide}"

    # Silent Mnemosyne recall (no visible block)
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
                    "\n\nYou have seen similar queries before:\n"
                    + "\n".join(entries)
                )

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
    """Save goal pattern to Mnemosyne after LLM response."""
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
            f"  Depth: {_state.depth} (1=goal, 2=goal+hats, 3=deep+reason_deeper)\n"
            f"  Critical mode: {'🔍 ON' if _state.critical_mode else 'OFF'}\n"
            f"  Mnemosyne: {'✅ connected' if MNEMOSYNE_AVAILABLE else '❌ unavailable'}\n"
            f"  Last complexity: {_state.last_complexity}"
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
        return "🔍 Critical analysis mode ON (adversarial pushback enabled)"
    if a == "critical off":
        _state.critical_mode = False
        return "🔍 Critical analysis mode OFF"
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
        "Usage: /meboya [on|off|status|depth 1-3|critical on|off|recall]\n"
        "  depth 1 = goal only\n"
        "  depth 2 = goal + hats (default)\n"
        "  depth 3 = goal + hats + critical pushback\n"
        "  critical on|off = toggle adversarial pushback reasoning\n"
        "  recall = show past goal patterns from Mnemosyne"
    )


# ──────────────────────────────────────────────────────────────────────
# Hermes entry point
# ──────────────────────────────────────────────────────────────────────

def register(ctx):
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("post_llm_call", _on_post_llm_call)
    ctx.register_command(
        name="meboya",
        handler=_cmd_meboya,
        description="Configure Meboya (on/off/status/depth/critical/recall)",
        args_hint="[on|off|status|depth 1-3|critical on|off|recall]",
    )
    logger.info(
        "meboya plugin registered (depth=%d, critical=%s, mnemosyne=%s)",
        _state.depth, _state.critical_mode, MNEMOSYNE_AVAILABLE,
    )