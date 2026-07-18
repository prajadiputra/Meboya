"""Meboya — Balinese for "questioning everything".

An auto-thinking plugin for Hermes Agent that injects structured prompts
(Goal Detection + Six Thinking Hats + Critical Mode) before each LLM call,
with optional Mnemosyne memory recall and write. Zero hard dependencies.

Hooks:
  pre_llm_call            → inject thinking guide + trace context
  post_llm_call           → save goal pattern to Mnemosyne

Compatible with Hermes Agent. Falls back gracefully if Mnemosyne is missing.
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

# Try newer API path first (mnemosyne-memory 3.12+)
try:
    from mnemosyne.core.memory import MemoryStream  # noqa: F401
    _mnemosyne = None
    del MemoryStream
except ImportError:
    pass

# Fall back to legacy Mnemosyne class (mnemosyne-memory 3.7–3.11)
if not MNEMOSYNE_AVAILABLE:
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
# Goal detection (matches standard Meboya/DOGA regex pattern)
# ──────────────────────────────────────────────────────────────────────

_GOAL_RE = re.compile(
    r"<world_model>.*?(Information|Understanding|Action)",
    re.DOTALL | re.IGNORECASE,
)


def _detect_goal_type(text: str) -> str:
    m = _GOAL_RE.search(text)
    return m.group(1).lower() if m else "unknown"


def _detect_complexity(text: str) -> Tuple[str, int]:
    """Heuristic — Meboya adds this on top of the standard approach."""
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

HATS_PROMPT = """Evaluate the situation through these parallel lenses:
  [WHITE] What are the objective facts, data, and constraints?
  [BLACK] What could go wrong? Risks, edge cases, pitfalls.
  [YELLOW] What are the upsides, opportunities, or value?
  [GREEN] What alternative approaches exist? Creative options.
  [BLUE] Synthesize the above — produce a clear conclusion.

Apply each lens in order. Never mix lenses in one section."""

# Critical mode — optional analytical enrichment
CRITICAL_HATS_PROMPT = """Evaluate the situation through these parallel lenses:
  [WHITE] What are the objective facts, data, and constraints?
  [BLACK] What could go wrong? Risks, edge cases, pitfalls.
   ├ CRITICAL: Is the premise itself valid? What assumptions may be wrong?
   ├ CRITICAL: What is the user NOT saying? Hidden requirements, unspoken constraints?
   └ CRITICAL: If this approach fails, what is the worst-case path?
  [RED] What is the gut reaction? What feels off? Trust the intuition signal.
  [YELLOW] What are the upsides, opportunities, or value?
  [GREEN] What alternative approaches exist? Creative options.
   ├ CRITICAL: What is the OPPOSITE approach? Argue against the default.
   └ CRITICAL: What would a domain expert do differently?
  [BLUE] Synthesize the above — produce a clear conclusion.
   ├ CRITICAL: Is this the BEST answer, or just the easiest acceptable one?
   ├ CRITICAL: Are second-order effects accounted for?
   └ CRITICAL: If challenged on this conclusion, can it be defended?

Apply each lens in order. Never mix lenses in one section.
Push back on the premise when warranted. Surface the dissenter view."""

LIGHT_PROMPT = GOAL_DETECTION
MEDIUM_PROMPT = f"{GOAL_DETECTION}\n\n{HATS_PROMPT}"
DEEP_PROMPT = f"""{GOAL_DETECTION}

{HATS_PROMPT}

After synthesis, call `reason_deeper` tool if analysis feels incomplete
(focus: "black hat cascade", "yellow hat assumptions", "green hat gaps")."""

CRITICAL_DEPTH_PROMPTS = {
    1: GOAL_DETECTION,
    2: f"{GOAL_DETECTION}\n\n{CRITICAL_HATS_PROMPT}",
    3: f"""{GOAL_DETECTION}

{CRITICAL_HATS_PROMPT}

After synthesis, call `reason_deeper` tool if analysis feels incomplete
(focus: 'second-order effects', 'opposing viewpoint', 'premise validity').""",
}

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
    last_complexity: str = "medium"
    show_trace: bool = True
    critical_mode: bool = False


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
    """Inject the Meboya thinking guide before the LLM sees the prompt."""
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

    # Inject relevant past goal patterns from Mnemosyne
    recall_block = ""
    if MNEMOSYNE_AVAILABLE:
        recalled = _recall(user_message, top_k=2)
        if recalled:
            entries = []
            for entry in recalled:
                content = entry.get("content", "")
                goal = entry.get("metadata", {}).get("goal_type", "?")
                entries.append(f"  - Past similar query (goal={goal}): {content[:120]}")
            if entries:
                recall_block = (
                    "\n\n[PAST CONTEXT — these were user goals for similar past queries. "
                    "Use this to calibrate your response approach.]\n"
                    + "\n".join(entries)
                )

    if _state.show_markers:
        injection = f"\n\n[Thinking Guide]\n{guide}{recall_block}\n[End Guide]"
    else:
        injection = f"\n\n{guide}{recall_block}"

    logger.debug(
        "meboya: injected depth=%d chars=%d recall=%d mnemosyne=%s",
        _state.depth, len(injection), 1 if recall_block else 0, MNEMOSYNE_AVAILABLE,
    )
    return injection


# ──────────────────────────────────────────────────────────────────────
# post_llm_call hook — save goal pattern to Mnemosyne
# ──────────────────────────────────────────────────────────────────────

_WORLD_MODEL_RE = re.compile(
    r"<world_model>\s*(.*?)\s*</world_model>",
    re.DOTALL | re.IGNORECASE,
)


def _extract_world_model(text: str) -> Tuple[List[str], str]:
    """Extract <world_model>...</world_model> blocks (returns blocks, remaining)."""
    blocks: List[str] = []
    remaining = text
    while True:
        match = _WORLD_MODEL_RE.search(remaining)
        if not match:
            break
        blocks.append(match.group(1).strip())
        remaining = remaining[:match.start()] + remaining[match.end():]
    return blocks, remaining.strip()


def _format_thinking_panel(blocks: List[str]) -> str:
    """Format world_model blocks into a clean Meboya panel."""
    non_empty = [b for b in blocks if b.strip()]
    if not non_empty:
        return ""
    lines = ["[MEBOYA: Telaah Proses]"]
    lines.append("   " + "=" * 50)
    for i, block in enumerate(non_empty, 1):
        if i > 1:
            lines.append("")
            lines.append("   . . . . . . . . . . . . . . . . . . . . . . . . . .")
            lines.append("")
        for line in block.strip().split("\n"):
            lines.append(f"   {line}")
    lines.append("")
    lines.append("   " + "=" * 50)
    return "\n".join(lines)


_HAT_TAGS = re.compile(r'\[(WHITE|RED|BLACK|YELLOW|GREEN|BLUE)\]', re.IGNORECASE)


def _detect_active_hats(text: str) -> List[str]:
    """Detect which hat tags appear in the response text."""
    return list(dict.fromkeys(
        m.group(1).lower() for m in _HAT_TAGS.finditer(text)
    ))


def _on_post_llm_call(
    response_text: str = "",
    user_message: str = "",
    **_: Any,
) -> None:
    """Save goal pattern to Mnemosyne after LLM response."""
    if not _state.enabled or not response_text:
        return

    # Detect goal from response (works if model outputs <world_model> tags)
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
            f"  Markers: {_state.show_markers}\n"
            f"  Trace display: {'ON' if _state.show_trace else 'OFF'}\n"
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
    if a == "markers on":
        _state.show_markers = True
        return "🏷️ Markers ON"
    if a == "markers off":
        _state.show_markers = False
        return "🏷️ Markers OFF"
    if a == "trace on":
        _state.show_trace = True
        return "📋 Trace display ON"
    if a == "trace off":
        _state.show_trace = False
        return "📋 Trace display OFF"
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
        "Usage: /meboya [on|off|status|depth 1-3|markers on|off|trace on|off|critical on|off|recall]\n"
        "  depth 1 = goal only\n"
        "  depth 2 = goal + hats (default)\n"
        "  depth 3 = depth 2 + reason_deeper\n"
        "  trace on|off = show/hide thinking trace in response\n"
        "  critical on|off = toggle adversarial pushback reasoning"
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
        description="Configure Meboya (on/off/status/depth/recall/critical)",
        args_hint="[on|off|status|depth 1-3|markers on|off|trace on|off|critical on|off|recall]",
    )
    logger.info(
        "meboya plugin registered (depth=%d, mnemosyne=%s, transform_hook=removed)",
        _state.depth, MNEMOSYNE_AVAILABLE,
    )