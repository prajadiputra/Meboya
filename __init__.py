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
HATS_PROMPT = """Output your answer using the exact template below. Replace the bracketed placeholders with your actual analysis.

<world_model>
Goal: [Information / Understanding / Action]
Complexity: [Low / Medium / High]
</world_model>

[WHITE] [facts and data about the user's question]
[BLACK] [risks, edge cases, pitfalls]
[YELLOW] [benefits, opportunities, value]
[GREEN] [alternatives, creative options]
[BLUE] [synthesis and recommendation]
[DECISION]
- Decision: [one-line verdict]
- Key Reason: [single most important factor]
- Risk Accepted: [what risk is worth taking]
- Action: [EXACT next step OR "No action needed — analysis complete"]

If Action is a concrete step (command, file edit, delegation), EXECUTE IT IMMEDIATELY after [DECISION]. Do not ask permission. If informational, end with the analysis.

Example (for "NATS vs Kafka in EKS"):
<world_model>
Goal: Information — comparison of two event broker options in Kubernetes
Complexity: Medium
</world_model>

[WHITE] NATS JetStream: single binary Go, ~50MB RAM, sub-ms latency, subject-based addressing. Kafka: JVM, GBs of RAM, partition/offset model, higher throughput ceiling.
[BLACK] NATS: smaller ecosystem, less tooling maturity. Kafka: JVM ops burden, more complex to deploy via Strimzi.
[YELLOW] NATS: simpler ops, lower resource cost, faster startup. Kafka: proven at massive scale, rich ecosystem (Connect, Streams, ksqlDB).
[GREEN] Hybrid: NATS for hot path, Kafka for audit log. Or Redis Streams as stepping stone before either.
[BLUE] Default to NATS JetStream unless throughput exceeds 100k msg/s or Kafka ecosystem tooling is required.
[DECISION]
- Decision: NATS JetStream as default event broker in EKS
- Key Reason: Operational simplicity + resource efficiency for typical workloads
- Risk Accepted: May need to migrate to Kafka if scale exceeds NATS ceiling
- Action: No action needed — analysis complete"""

# Critical mode — adversarial pushback
CRITICAL_HATS_PROMPT = """Output your answer using the exact template below. Replace the bracketed placeholders with your actual analysis.

<world_model>
Goal: [Information / Understanding / Action]
Complexity: [Low / Medium / High]
</world_model>

[WHITE] [facts and data about the user's question]
[BLACK] [risks, edge cases, pitfalls]
  ├ CRITICAL: [premise challenge — is the user's assumption valid?]
  ├ CRITICAL: [what is the user NOT saying?]
  └ CRITICAL: [worst-case path if this approach fails]
[RED] [gut reaction — what feels off or uncertain?]
[YELLOW] [benefits, opportunities, value]
[GREEN] [alternatives, creative options]
  ├ CRITICAL: [what is the OPPOSITE approach?]
  └ CRITICAL: [what would a domain expert do differently?]
[BLUE] [synthesis and recommendation]
  ├ CRITICAL: [is this the BEST answer or just the easiest?]
  └ CRITICAL: [are second-order effects accounted for?]
[DECISION]
- Decision: [one-line verdict]
- Key Reason: [single most important factor]
- Risk Accepted: [what risk is worth taking]
- Action: [EXACT next step OR "No action needed — analysis complete"]

If Action is a concrete step (command, file edit, delegation), EXECUTE IT IMMEDIATELY after [DECISION]. Do not ask permission. If informational, end with the analysis.

Example (for "NATS vs Kafka in EKS"):
<world_model>
Goal: Action — choose event broker for new EKS service
Complexity: Medium
</world_model>

[WHITE] NATS: single binary, ~50MB, sub-ms latency. Kafka: JVM, >6GB RAM, higher throughput ceiling. Current workload ~25k msg/s.
[BLACK] NATS ecosystem maturity risk. Kafka: higher ops overhead, Strimzi complexity.
  ├ CRITICAL: Is 25k msg/s projected to grow? Non-functional requirements undefined.
  ├ CRITICAL: Team skill not disclosed — Kafka expertise available?
  └ CRITICAL: If NATS fails during peak, no fallback path?
[RED] NATS feels lighter for team size, but Kafka feels safer for future scale.
[YELLOW] NATS: faster delivery, simpler debugging. Kafka: industry standard, easier to hire for.
[GREEN] Hybrid: NATS for real-time path, Kafka for audit sink. Or skip NATS and use Kafka from day 1.
  ├ CRITICAL: Opposite approach: commit to Kafka now despite overhead — fewer future migrations.
  └ CRITICAL: Domain expert: "Use NATS if <50k msg/s and team <5, else Kafka."
[BLUE] Start with NATS JetStream given current load/team size. Add Kafka connector for audit sink when needed.
  ├ CRITICAL: This is the best answer for current constraints, but revisit in 6 months.
  └ CRITICAL: Second-order: NATS-to-Kafka migration cost is lower than maintaining Kafka from day 1.
[DECISION]
- Decision: NATS JetStream as primary, Kafka connector for audit only
- Key Reason: Operational simplicity matches current team size and throughput (25k msg/s)
- Risk Accepted: Migration risk if workload exceeds 100k msg/s
- Action: No action needed — analysis complete"""

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

    # Build injection — guide with [Thinking Guide] wrapper + explicit output instruction
    injection = f"\n\n[Thinking Guide]\n{guide}\n\nNow produce your answer with the hat tags and [DECISION] block as instructed above.\n[End Guide]"

    # Mnemosyne recall with [PAST CONTEXT] block
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
                    "Use this to calibrate your response approach.]\n"
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