"""auto-thinking — Zero-dep Six Hats + Goal Detection + Mnemosyne for Hermes.

Hooks:
  pre_llm_call       → recall past patterns + inject [world_model_guide]
  transform_llm_output → strip markers + write goal to Mnemosyne

No hard dependencies on Mnemosyne — graceful fallback.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Optional Mnemosyne (same import pattern as DOGA for compatibility)
# ──────────────────────────────────────────────────────────────────────

MNEMOSYNE_AVAILABLE = False
_mnemosyne = None

# -- attempt newer path first (mnemosyne-memory 3.12+) --
try:
    from mnemosyne.core.memory import MemoryStream  # noqa: F401
    _mnemosyne = None
    del MemoryStream
except ImportError:
    pass

# -- attempt DOGA / legacy path (mnemosyne-memory 3.7–3.11) --
if not MNEMOSYNE_AVAILABLE:
    try:
        from mnemosyne import Mnemosyne
        _mnemosyne = Mnemosyne()
        MNEMOSYNE_AVAILABLE = True
        logger.info("auto-thinking: Mnemosyne connected (legacy import path)")
    except ImportError as e:
        logger.debug("auto-thinking: no mnemosyne: %s", e)
    except Exception as e:
        logger.warning("auto-thinking: mnemosyne init failed: %s", e)


def _remember(content: str, importance: float = 0.7, source: str = "auto-thinking",
              metadata: Optional[Dict] = None) -> str | None:
    """Write memory entry. Returns id or None."""
    if not MNEMOSYNE_AVAILABLE or not _mnemosyne:
        return None
    try:
        kwargs = {"content": content, "importance": importance, "source": source}
        if metadata:
            kwargs["metadata"] = metadata
        return _mnemosyne.remember(**kwargs)
    except Exception as e:
        logger.debug("auto-thinking: _remember failed: %s", e)
        return None


def _recall(query: str, top_k: int = 3) -> List[Dict]:
    """Recall past memory entries. Returns list of dicts."""
    if not MNEMOSYNE_AVAILABLE or not _mnemosyne:
        return []
    try:
        return _mnemosyne.recall(query, top_k=top_k) or []
    except Exception as e:
        logger.debug("auto-thinking: _recall failed: %s", e)
        return []


# ──────────────────────────────────────────────────────────────────────
# Goal detection (compact, accurate — matches DOGA's regex pattern)
# ──────────────────────────────────────────────────────────────────────

_GOAL_RE = re.compile(
    r"<world_model>.*?(Information|Understanding|Action)",
    re.DOTALL | re.IGNORECASE,
)


def _detect_goal_type(text: str) -> str:
    m = _GOAL_RE.search(text)
    return m.group(1).lower() if m else "unknown"


def _detect_task_complexity(text: str) -> Tuple[str, int]:
    """Return (label, score 0-100) from keyword heuristics."""
    low = 0
    for kw in ["simple", "trivial", "what is", "who is", "when is", "define", "show me",
               "ls ", "cat ", "find ", "grep "]:
        if kw in text.lower():
            low += 1
    high = 0
    for kw in ["deploy", "architecture", "optimize", "refactor", "migrate", "security",
               "incident", "cost", "troubleshoot", "latency", "scale"]:
        if kw in text.lower():
            high += 1
    if high >= 2:
        return ("high", 80 + min(high * 5, 20))
    if low >= 2:
        return ("low", 20 + min(low * 5, 20))
    return ("medium", 50)


# ──────────────────────────────────────────────────────────────────────
# Prompt templates
# ──────────────────────────────────────────────────────────────────────

GOAL_DETECTION = """Before answering, briefly identify what the user's primary need is:

- **Information**: They want factual data, analysis, or explanation.
- **Understanding**: They want to feel heard, validated, or understood.
- **Action**: They want a decision, recommendation, or next step.

Choose the dominant goal and let it shape your response."""

HATS_PROMPT = """Evaluate the situation through these parallel lenses:
  [WHITE] What are the objective facts, data, and constraints?
  [BLACK] What could go wrong? Risks, edge cases, pitfalls.
  [YELLOW] What are the upsides, opportunities, or value?
  [GREEN] What alternative approaches exist? Creative options.
  [BLUE] Synthesize the above — produce a clear conclusion.

Apply each lens in order. Never mix lenses in one section."""

LIGHT_PROMPT = GOAL_DETECTION
MEDIUM_PROMPT = f"{GOAL_DETECTION}\n\n{HATS_PROMPT}"
DEEP_PROMPT = f"""{GOAL_DETECTION}

{HATS_PROMPT}

After synthesis, call `reason_deeper` tool if analysis feels incomplete
(focus: "black hat cascade", "yellow hat assumptions", "green hat gaps")."""

DEPTH_PROMPTS = {1: LIGHT_PROMPT, 2: MEDIUM_PROMPT, 3: DEEP_PROMPT}

# ──────────────────────────────────────────────────────────────────────
# Plugin state
# ──────────────────────────────────────────────────────────────────────

class _State:
    enabled: bool = True
    depth: int = 2
    show_markers: bool = True
    last_user_message: str = ""
    last_goal_type: str = "unknown"

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
    """Inject thinking guide + recall past patterns before LLM call."""
    if not _state.enabled:
        return None

    # Store for later write
    _state.last_user_message = user_message

    # Skip very short messages
    if len(user_message.strip()) < 15 and not is_first_turn:
        return None

    # Don't double-inject
    if "[world_model_guide]" in user_message:
        return None

    guide = DEPTH_PROMPTS.get(_state.depth, MEDIUM_PROMPT)

    # ── Recall past relevant goal patterns ──
    recall_block = ""
    if MNEMOSYNE_AVAILABLE:
        recalled = _recall(user_message, top_k=2)
        if recalled:
            entries = []
            for entry in recalled:
                content = entry.get("content", "")
                goal = entry.get("metadata", {}).get("goal_type", "") or _detect_goal_type(content)
                entries.append(f"  - Past similar query (goal={goal}): {content[:120]}")
            if entries:
                recall_block = (
                    "\n\n[PAST CONTEXT — these were user goals for similar past queries. "
                    "Use this to calibrate your response approach.]\n"
                    + "\n".join(entries)
                )

    if _state.show_markers:
        injection = f"\n\n[world_model_guide]\n{guide}{recall_block}\n[/world_model_guide]"
    else:
        injection = f"\n\n{guide}{recall_block}"

    logger.debug(
        "auto-thinking: injected depth=%d chars=%d recall=%d mnemosyne=%s",
        _state.depth, len(injection), 1 if recall_block else 0, MNEMOSYNE_AVAILABLE,
    )
    return injection


def _on_transform_llm_output(response_text: str = "", **_: Any) -> Optional[str]:
    """Strip markers + write goal to Mnemosyne."""
    # ── Write goal pattern ──
    goal_type = "unknown"
    if _state.last_user_message and response_text:
        goal_type = _detect_goal_type(response_text)
        complexity_label, complexity_score = _detect_task_complexity(
            _state.last_user_message
        )
        _remember(
            content=_state.last_user_message,
            importance=0.7,
            metadata={
                "goal_type": goal_type,
                "complexity": complexity_label,
                "complexity_score": complexity_score,
                "depth": _state.depth,
                "mnemosyne_version": "3.11",
            },
        )
        _state.last_goal_type = goal_type

    # ── Strip leaked guide blocks ──
    if not _state.show_markers:
        return None
    cleaned = re.sub(
        r"\[world_model_guide\].*?\[/world_model_guide\]",
        "",
        response_text,
        flags=re.DOTALL,
    )
    return cleaned if cleaned != response_text else None


# ──────────────────────────────────────────────────────────────────────
# /thinking command
# ──────────────────────────────────────────────────────────────────────

def _cmd_thinking(args: str, **_: Any) -> str:
    global _state
    a = args.strip().lower() if args else "status"

    if a == "on":
        _state.enabled = True
        return "✅ Auto-thinking ENABLED"
    if a == "off":
        _state.enabled = False
        return "🛑 Auto-thinking DISABLED"
    if a == "status":
        return (
            f"📊 Auto-thinking status:\n"
            f"  Enabled: {_state.enabled}\n"
            f"  Depth: {_state.depth} (1=goal, 2=goal+hats, 3=deep+reason_deeper)\n"
            f"  Markers: {_state.show_markers}\n"
            f"  Mnemosyne: {'✅ connected' if MNEMOSYNE_AVAILABLE else '❌ unavailable'}\n"
            f"  Last goal: {_state.last_goal_type}"
        )
    if a.startswith("depth"):
        try:
            d = int(a.split()[1])
            if 1 <= d <= 3:
                _state.depth = d
                return f"🎯 Depth set to {d} ({DEPTH_PROMPTS[d][:60]}...)"
        except (IndexError, ValueError):
            pass
        return "Usage: /thinking depth 1|2|3"
    if a == "markers on":
        _state.show_markers = True
        return "🏷️ Markers ON"
    if a == "markers off":
        _state.show_markers = False
        return "🏷️ Markers OFF"
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
        "Usage: /thinking [on|off|status|depth 1-3|markers on|off|recall]\n"
        "  depth 1 = goal only\n"
        "  depth 2 = goal + hats (default)\n"
        "  depth 3 = depth 2 + reason_deeper"
    )


# ──────────────────────────────────────────────────────────────────────
# Hermes entry point
# ──────────────────────────────────────────────────────────────────────

def register(ctx):
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("transform_llm_output", _on_transform_llm_output)
    ctx.register_command(
        name="thinking",
        description="Configure auto-thinking (on/off/status/depth/recall)",
        handler=_cmd_thinking,
        args_hint="[on|off|status|depth 1-3|markers on|off|recall]",
    )
    logger.info(
        "auto-thinking v0.2 registered (depth=%d, mnemosyne=%s)",
        _state.depth, MNEMOSYNE_AVAILABLE,
    )