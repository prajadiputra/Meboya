"""
Meboya — Auto-thinking plugin with De Bono Six Hats + Monte Carlo reasoning + Goal detection.
Upgraded with Self-Verification (Logical checks) and Knowledge Boundary (Hallucination detection).
"""

from __future__ import annotations

import ast
import json
import logging
import math
import random
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("meboya")

# ---------------------------------------------------------------------------
# Mnemosyne graceful fallback (two import paths)
# ---------------------------------------------------------------------------
MNEMOSYNE_AVAILABLE = False
_mnemosyne = None

# Try newer API path first (mnemosyne-memory 3.12+)
try:
    from mnemosyne.core.memory import MemoryStream

    _mnemosyne = None
    del MemoryStream
except ImportError:
    pass

# Fall back to legacy Mnemosyne class (3.7–3.11)
if not MNEMOSYNE_AVAILABLE:
    try:
        from mnemosyne import Mnemosyne

        _mnemosyne = Mnemosyne()
        MNEMOSYNE_AVAILABLE = True
    except ImportError:
        logger.debug("mnemosyne not installed — graceful fallback")
    except Exception as e:
        logger.warning("mnemosyne init failed: %s", e)


def remember(**kwargs: Any) -> None:
    if MNEMOSYNE_AVAILABLE and _mnemosyne:
        _mnemosyne.remember(**kwargs)


def recall(query: str, **kwargs: Any) -> List[Dict[str, Any]]:
    if MNEMOSYNE_AVAILABLE and _mnemosyne:
        return _mnemosyne.recall(query=query, **kwargs)
    return []


# ---------------------------------------------------------------------------
# De Bono Six Thinking Hats
# ---------------------------------------------------------------------------

HATS = {
    "white": {
        "name": "White Hat",
        "emoji": "⚪",
        "focus": "Facts, data, information gaps. What do we know? What do we need?",
    },
    "red": {
        "name": "Red Hat",
        "emoji": "🔴",
        "focus": "Feelings, intuition, hunches. No justification needed.",
    },
    "black": {
        "name": "Black Hat",
        "emoji": "⚫",
        "focus": "Risks, problems, why it might fail. Critical judgment.",
    },
    "yellow": {
        "name": "Yellow Hat",
        "emoji": "🟡",
        "focus": "Benefits, optimism, value. Why it could work.",
    },
    "green": {
        "name": "Green Hat",
        "emoji": "🟢",
        "focus": "Creativity, alternatives, new ideas. Provocation.",
    },
    "blue": {
        "name": "Blue Hat",
        "emoji": "🔵",
        "focus": "Process, meta-thinking, summary, next steps. Orchestration.",
    },
}

HAT_ORDER = ["white", "red", "black", "yellow", "green", "blue"]


def build_hat_guidance(depth: int = 3) -> str:
    """Build De Bono hat guidance block for injection."""
    if depth <= 2:
        return """

[De Bono Parallel Thinking]
Use the Six Thinking Hats to structure your reasoning.
Mark each section with a simple prefix tag:
[WHITE] facts/data | [RED] feelings/intuition | [BLACK] risks/caution
[YELLOW] benefits/optimism | [GREEN] creativity/alternatives | [BLUE] process/summary
Apply hats as useful. Keep hat sections VISIBLE in your output."""

    lines = ["", "[De Bono Parallel Thinking — Structured]"]
    for hat_key in HAT_ORDER:
        hat = HATS[hat_key]
        tag = hat_key.upper()
        lines.append(f"\n[{tag}] {hat['name']} — {hat['focus']}")

    lines.append(
        "\nProcess: Work through hats in order (WHITE → RED → BLACK → YELLOW → GREEN → BLUE). "
        "BLUE synthesizes at the end. Keep ALL hat sections VISIBLE in your final output."
    )
    return "\n".join(lines)


def detect_active_hats(response_text: str) -> List[str]:
    """Detect which hats were used in the response."""
    active = []
    for hat_key in HATS:
        if re.search(rf"\[HAT:{hat_key}\].*?\[/HAT:{hat_key}\]", response_text, re.DOTALL | re.IGNORECASE):
            active.append(hat_key)
    return active


# ---------------------------------------------------------------------------
# Auto-Depth Complexity Selector (pure Python, 0 LLM tokens)
# ---------------------------------------------------------------------------


@dataclass
class ComplexityFeatures:
    length: int = 0
    question_marks: int = 0
    code_blocks: int = 0
    technical_terms: int = 0
    conditional_keywords: int = 0
    multi_part: int = 0


TECH_TERMS = {
    # Infra & networking
    "cloudflare",
    "gateway",
    "ingress",
    "dns",
    "cdn",
    "load balancer",
    "load-balancer",
    "lb",
    "reverse proxy",
    "tls",
    "ssl",
    "cert",
    "cname",
    "a record",
    "txt record",
    "mx record",
    # Servers & cloud
    "server",
    "deploy",
    "deployment",
    "cluster",
    "instance",
    "vm",
    "vps",
    "hosting",
    "domain",
    # Cloudflare-specific
    "tunnel",
    "cloudflared",
    "warp",
    "workers",
    "pages",
    "r2",
    "d1",
    "kv",
    "zone",
    "dns_record",
    "waf rule",
    "rate limit",
    # Status / live queries (auto-promote to medium)
    "status",
    "current",
    "saat ini",
    "live",
    "real-time",
    "realtime",
    "now",
    "check",
    "cek",
    "monitoring",
    "monitor",
    "alert",
    "incident",
    "downtime",
    "outage",
    "uptime",
    "health check",
    # Original technical terms below
    "kubernetes",
    "docker",
    "aws",
    "terraform",
    "ansible",
    "python",
    "javascript",
    "typescript",
    "api",
    "database",
    "sql",
    "redis",
    "kafka",
    "microservice",
    "distributed",
    "concurrency",
    "deadlock",
    "race condition",
    "memory leak",
    "optimization",
    "latency",
    "throughput",
    "scalability",
    "architecture",
    "design pattern",
    "refactor",
    "debug",
    "profiling",
    "benchmark",
    "regression",
    "ci/cd",
    "pipeline",
    "monitoring",
    "observability",
    "tracing",
    "logging",
    "alerting",
    "slo",
    "sli",
    "error budget",
    "postmortem",
    "root cause",
    "capacity planning",
    "cost optimization",
    "security",
    "vulnerability",
    "compliance",
    "encryption",
    "authentication",
    "authorization",
    "oauth",
    "jwt",
    "rbac",
    "abac",
    "zero trust",
    "network policy",
    "service mesh",
    "istio",
    "linkerd",
    "envoy",
    "grpc",
    "rest",
    "graphql",
    "websocket",
    "message queue",
    "event driven",
    "saga",
    "cqrs",
    "event sourcing",
}

CONDITIONAL_KEYWORDS = {
    "if",
    "else",
    "elif",
    "unless",
    "when",
    "depends",
    "conditional",
    "scenario",
    "case",
    "option",
    "alternative",
    "tradeoff",
    "pros and cons",
    "compare",
    "versus",
    "vs",
    "either",
    "or",
    "maybe",
    "perhaps",
    "might",
    "could",
    "would",
    "should",
    "weigh",
    "balance",
    "decide",
    "choose",
    "select",
    "evaluate",
    "assess",
}


def assess_complexity(text: str) -> str:
    """Return 'low' | 'medium' | 'high' — pure Python heuristic."""
    if not isinstance(text, str) or not text.strip():
        return "low"

    features = ComplexityFeatures()
    features.length = len(text)
    features.question_marks = text.count("?")
    features.code_blocks = text.count("```")
    features.multi_part = max(1, text.count("?") + text.count(";") // 2)

    lower = text.lower()
    features.technical_terms = sum(1 for term in TECH_TERMS if term in lower)
    features.conditional_keywords = sum(1 for kw in CONDITIONAL_KEYWORDS if kw in lower)

    # Scoring (tuned for infra/technical)
    score = 0
    score += min(features.length // 80, 8)  # Lebih sensitif
    score += min(features.question_marks * 2, 5)
    score += min(features.code_blocks * 3, 6)
    score += min(features.technical_terms * 3, 12)  # Term bobot tinggi
    score += min(features.conditional_keywords * 1.5, 6)
    score += min(features.multi_part * 2, 5)

    # Auto-promote: any technical term → minimum medium
    if features.technical_terms >= 1:
        score = max(score, 8)
    # 2+ tech terms → minimum high
    if features.technical_terms >= 2:
        score = max(score, 16)

    if score <= 6:
        return "low"
    elif score <= 15:
        return "medium"
    return "high"


def depth_from_complexity(complexity: str) -> int:
    """Map complexity to depth 1-5."""
    return {"low": 1, "medium": 3, "high": 5}[complexity]


# ---------------------------------------------------------------------------
# Monte Carlo Simulation Engine (AST-safe)
# ---------------------------------------------------------------------------

ALLOWED_NODES = {
    ast.Expression,
    ast.BoolOp,
    ast.UnaryOp,
    ast.BinOp,
    ast.Compare,
    ast.Name,
    ast.Constant,
    ast.Load,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Is,
    ast.IsNot,
    ast.In,
    ast.NotIn,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
}


def _validate_ast(node: ast.AST) -> bool:
    """Check AST contains only whitelisted nodes."""
    for child in ast.walk(node):
        if type(child) not in ALLOWED_NODES:
            return False
    return True


def _compile_condition(condition: str):
    """Compile a condition string to a safe callable."""
    try:
        tree = ast.parse(condition, mode="eval")
    except SyntaxError:
        return None
    if not _validate_ast(tree):
        return None
    code = compile(tree, "<condition>", "eval")
    return lambda vars_dict: eval(code, {"__builtins__": {}}, vars_dict)


class MonteCarloEngine:
    """Thread-local Monte Carlo engine for simulation tool."""

    def __init__(self):
        self._local = threading.local()

    def _get_rng(self) -> random.Random:
        if not hasattr(self._local, "rng"):
            self._local.rng = random.Random()
        return self._local.rng

    def simulate(
        self,
        scenarios: List[Dict[str, Any]],
        n_iterations: int = 10000,
    ) -> Dict[str, Any]:
        """Run Monte Carlo simulation over scenarios."""
        if not scenarios:
            return {"error": "No scenarios provided"}

        rng = self._get_rng()
        n_iterations = max(100, min(n_iterations, 100000))

        compiled = []
        all_variables = set()
        for sc in scenarios:
            name = sc.get("name", "unnamed")
            variables = sc.get("variables", {})
            conditions = sc.get("conditions", [])
            for var in variables:
                all_variables.add(var)

            cond_fns = []
            for cond in conditions:
                fn = _compile_condition(cond)
                if fn is None:
                    return {"error": f"Invalid condition in scenario '{name}': {cond}"}
                cond_fns.append(fn)

            compiled.append({"name": name, "variables": variables, "conditions": cond_fns})

        wins = {sc["name"]: 0 for sc in compiled}
        samples = {sc["name"]: [] for sc in compiled}

        for _ in range(n_iterations):
            for sc in compiled:
                vars_dict = {}
                for var_name, prob in sc["variables"].items():
                    vars_dict[var_name] = 1 if rng.random() < prob else 0

                if all(fn(vars_dict) for fn in sc["conditions"]):
                    wins[sc["name"]] += 1
                    samples[sc["name"]].append(vars_dict)

        # Calculate probabilities, Wilson score CI, and Sensitivity Analysis
        results = {}
        for name in wins:
            wins_count = wins[name]
            prob = wins_count / n_iterations
            
            # 95% Confidence Interval (Wilson score interval)
            z = 1.96
            denominator = 1 + z**2 / n_iterations
            centre_adj_val = prob + z**2 / (2 * n_iterations)
            step = z * math.sqrt((prob * (1 - prob) + z**2 / (4 * n_iterations)) / n_iterations)
            ci_lower = max(0.0, round((centre_adj_val - step) / denominator, 4))
            ci_upper = min(1.0, round((centre_adj_val + step) / denominator, 4))

            # Sensitivity Analysis: how much does flipping a variable affect the match rate?
            sensitivity = {}
            for sc in compiled:
                if sc["name"] == name and sc["variables"]:
                    for var in sc["variables"]:
                        # Calculate impact: if var is forced True vs False
                        forced_true_matches = 0
                        forced_false_matches = 0
                        test_runs = min(1000, n_iterations)
                        for _ in range(test_runs):
                            vars_dict_true = {}
                            vars_dict_false = {}
                            for v, p in sc["variables"].items():
                                val = 1 if rng.random() < p else 0
                                vars_dict_true[v] = val
                                vars_dict_false[v] = val
                            vars_dict_true[var] = 1
                            vars_dict_false[var] = 0
                            if all(fn(vars_dict_true) for fn in sc["conditions"]):
                                forced_true_matches += 1
                            if all(fn(vars_dict_false) for fn in sc["conditions"]):
                                forced_false_matches += 1
                        impact = (forced_true_matches - forced_false_matches) / test_runs
                        sensitivity[var] = round(impact, 4)

            results[name] = {
                "probability": round(prob, 4),
                "confidence_interval_95": [ci_lower, ci_upper],
                "wins": wins_count,
                "iterations": n_iterations,
                "sensitivity_impact": sensitivity,
                "sample_vars": samples[name][:3] if samples[name] else [],
            }

        winner = max(results.items(), key=lambda x: x[1]["probability"])[0]

        return {
            "scenarios": results,
            "winner": winner,
            "total_iterations": n_iterations,
            "confidence": "high" if n_iterations >= 5000 else "medium",
        }
# ---------------------------------------------------------------------------
# Goal Detection
# ---------------------------------------------------------------------------

GOAL_TYPES = ["information", "understanding", "action"]

GOAL_DETECTION_PROMPT = """Before answering, briefly identify what the user's primary need is:

- **Information**: They want factual data, analysis, or explanation.
- **Understanding**: They want to feel heard, validated, or understood.
- **Action**: They want a decision, recommendation, or next step.

Choose the dominant goal and let it shape your response."""


def extract_goal_from_response(response_text: str) -> str:
    """Extract goal type from <world_model> block in response."""
    match = re.search(
        r"<world_model>.*?(Information|Understanding|Action)",
        response_text,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group(1).lower()
    return "unknown"


# ---------------------------------------------------------------------------
# Prompt Templates (Upgraded with Verification & Knowledge Boundary)
# ---------------------------------------------------------------------------

SCENARIO_PROMPT_TEMPLATE = """Consider multiple possible scenarios or interpretations of this question.
For each scenario, think about:
1. What would need to be true for this scenario to hold?
2. How likely is it relative to the alternatives?
3. What would change if this scenario is wrong?

Use the `<world_model>` tag for your internal reasoning, like:
<world_model>
## Scenarios
1. **Scenario A** — what it assumes, rough likelihood
2. **Scenario B** — what it assumes, rough likelihood
</world_model>

If you can identify specific variables with probabilities, call the
`simulate` tool to run a Monte Carlo analysis."""

SIMULATION_TOOL_GUIDANCE = """You have access to the `simulate` tool for quantitative probability analysis.
Call it when you need to weigh multiple factors with uncertainty."""

REASON_DEEPER_GUIDANCE = """You have access to the `reason_deeper` tool for recursive self-critique.
Call it after your initial `<world_model>` analysis to identify what you missed,
challenge assumptions, and refine your reasoning."""

# NEW: Self-Verification guidelines injected into <world_model> loop
SELF_VERIFICATION_PROMPT = """
[SELF-VERIFICATION GATE]
Before finalizing your output, audit your reasoning inside the `<world_model>` tag:
1. **Fact Check**: Identify exact statements you assume to be true. Are you 100% sure?
2. **Logical Flow**: Does your premise directly lead to the conclusion, or is there a gap?
3. **Edge Cases**: What happens if your main assumption fails?
4. **Tool Verification**: Did you verify output from tools, or assume they worked?
"""

# NEW: Knowledge Boundary guidelines
KNOWLEDGE_BOUNDARY_PROMPT = """
[KNOWLEDGE BOUNDARY RULES]
If your query involves:
- Current release versions, API parameters, or command flags not in context.
- Remote endpoints, package listings, or live system state.
- Highly specific error logs or hardware compatibility.
And you are recalling from training data without live verification:
**You MUST call a retrieval tool (e.g. `web_search`, `read_file`, `search_files`) first.**
If a search fails or no tool is available, you MUST explicitly state inside your `<world_model>`:
`[KNOWLEDGE GAP: Reason why you cannot verify]`
"""

LIGHT_PROMPT = f"{GOAL_DETECTION_PROMPT}\n{KNOWLEDGE_BOUNDARY_PROMPT}"

MEDIUM_PROMPT = f"""{GOAL_DETECTION_PROMPT}

{SCENARIO_PROMPT_TEMPLATE}

{REASON_DEEPER_GUIDANCE}

{SELF_VERIFICATION_PROMPT}
{KNOWLEDGE_BOUNDARY_PROMPT}"""

COUNTERFACTUAL_GUIDANCE = """
[COUNTERFACTUAL EXPLORER]
For your final synthesis, consider:
1. "What if my main assumption is wrong?"
2. "What are the contingency plans if this fails at 80% completion?"
3. "Is there a 'kill-switch' or rollback plan?"
Generate a brief contingency summary if the path has high risk."""

DEEP_PROMPT = f"""{GOAL_DETECTION_PROMPT}

{SCENARIO_PROMPT_TEMPLATE}

{SIMULATION_TOOL_GUIDANCE}

{REASON_DEEPER_GUIDANCE}

{SELF_VERIFICATION_PROMPT}
{KNOWLEDGE_BOUNDARY_PROMPT}
{COUNTERFACTUAL_GUIDANCE}"""


def build_prompt(depth: int = 3) -> str:
    """Return appropriate prompt text for depth 1-5."""
    if depth <= 2:
        return LIGHT_PROMPT
    elif depth <= 4:
        return MEDIUM_PROMPT
    return DEEP_PROMPT


def build_goal_prompt(
    user_message: str,
    depth: int = 3,
    past_patterns: Optional[List[Dict]] = None,
    hats_enabled: bool = True,
) -> str:
    """Build complete thinking guidance block for pre_llm_call injection."""
    prompt = build_prompt(depth)

    if hats_enabled:
        prompt += build_hat_guidance(depth)

    if past_patterns:
        lines = ["", "Previous patterns for similar queries:"]
        for p in past_patterns:
            lines.append(f"- Goal: {p.get('goal_type', '?')} (used {p.get('count', 1)}x)")
        prompt += "\n" + "\n".join(lines)

    return f"\n\n[meboya_guide]\n{prompt}\n[/meboya_guide]"


# ---------------------------------------------------------------------------
# Output Formatter
# ---------------------------------------------------------------------------


def format_response(
    response_text: str,
    show_simulation: bool = True,
    active_hats: Optional[List[str]] = None,
) -> str:
    """Format response: strip guide blocks, optionally append hat summary."""
    cleaned = re.sub(
        r"\[meboya_guide\].*?\[/meboya_guide\]", "", response_text, flags=re.DOTALL
    )
    cleaned = re.sub(
        r"\[world_model_guide\].*?\[/world_model_guide\]", "", cleaned, flags=re.DOTALL
    )
    cleaned = re.sub(r"<world_model>.*?</world_model>", "", cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip()

    if show_simulation and active_hats:
        hat_summary = "\n\n---\n**Thinking Hats Used:** " + " → ".join(
            f"{HATS[h]['emoji']} {HATS[h]['name']}" for h in active_hats if h in HATS
        )
        cleaned += hat_summary

    return cleaned


# ---------------------------------------------------------------------------
# Plugin State
# ---------------------------------------------------------------------------


@dataclass
class PluginState:
    enabled: bool = True
    show_simulation: bool = True
    memory_enabled: bool = MNEMOSYNE_AVAILABLE
    auto_depth: bool = True
    depth: int = 3
    max_recursion: int = 3
    hats_enabled: bool = True
    _recursion_depth: int = 0
    _reasoning_stack: List[Dict] = field(default_factory=list)
    _active_hats: List[str] = field(default_factory=list)
    _current_user_message: str = ""
    _stop_sent: bool = False


_state = PluginState()
_engine = MonteCarloEngine()


# ---------------------------------------------------------------------------
# Tool: simulate
# ---------------------------------------------------------------------------

SIMULATE_SCHEMA = {
    "name": "simulate",
    "description": (
        "Run a Monte Carlo simulation over probabilistic scenarios. "
        "Provide scenarios with variable probabilities and optional logical conditions. "
        "Returns probability distribution and uncertainty metrics. "
        "Use this when you need to quantitatively weigh multiple uncertain factors."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "scenarios": {
                "type": "array",
                "description": "List of scenarios to simulate.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Short label for this scenario (e.g. 'contract_valid').",
                        },
                        "variables": {
                            "type": "object",
                            "description": (
                                "Variable name → probability (0.0–1.0). "
                                "Each variable represents an independent binary factor. "
                                "Example: {'signature_ok': 0.8, 'duress': 0.1}"
                            ),
                            "additionalProperties": {"type": "number"},
                        },
                        "conditions": {
                            "type": "array",
                            "description": "Logical conditions (Python expressions) that must all be true.",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["name", "variables"],
                },
            },
            "n_iterations": {
                "type": "integer",
                "description": "Number of Monte Carlo iterations (default 10000, max 100000).",
                "default": 10000,
                "minimum": 100,
                "maximum": 100000,
            },
        },
        "required": ["scenarios"],
    },
}


async def simulate_tool_handler(args: Dict[str, Any]) -> str:
    """Handler for the simulate tool."""
    scenarios = args.get("scenarios", [])
    n_iterations = args.get("n_iterations", 10000)

    result = _engine.simulate(scenarios, n_iterations)
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Tool: reason_deeper
# ---------------------------------------------------------------------------

REASON_DEEPER_SCHEMA = {
    "name": "reason_deeper",
    "description": (
        "Recursive self-critique tool. After your initial <world_model> analysis, "
        "call this to identify what you missed, challenge assumptions, and refine reasoning. "
        "Specify a focus area (e.g. 'risk cascade', 'hidden assumptions')."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "focus": {
                "type": "string",
                "description": "Aspect to dig deeper into (e.g. 'risk cascade', 'hidden assumptions').",
            },
            "current_reasoning": {
                "type": "string",
                "description": "Your current <world_model> reasoning to critique.",
            },
        },
        "required": ["focus"],
    },
}


async def reason_deeper_tool_handler(args: Dict[str, Any]) -> str:
    """Handler for the reason_deeper tool."""
    focus = args.get("focus", "")
    current = args.get("current_reasoning", "")

    _state._recursion_depth += 1
    _state._reasoning_stack.append(
        {"level": _state._recursion_depth, "focus": focus, "reasoning": current[:500]}
    )

    critique = f"""[REASON_DEEPER — Level {_state._recursion_depth}/{_state.max_recursion}]
Focus: {focus}

Your previous reasoning:
{current}

Now critically examine:
1. What assumptions are untested?
2. What scenarios did you miss?
3. What would change your conclusion?
4. Are there second-order effects?

Return refined <world_model> analysis."""

    return critique


# ---------------------------------------------------------------------------
# Hook: pre_llm_call (context injection)
# ---------------------------------------------------------------------------


async def on_pre_llm_call(
    user_message: str = "",
    conversation_history: Optional[List] = None,
    session_id: str = "",
    **_: Any,
) -> Optional[Dict[str, str]]:
    """Inject thinking guidance before LLM call."""
    if not _state.enabled:
        return None

    _state._current_user_message = user_message
    _state._recursion_depth = 0
    _state._reasoning_stack.clear()

    if _state.auto_depth:
        complexity = assess_complexity(user_message)
        depth = depth_from_complexity(complexity)
    else:
        depth = _state.depth

    past_patterns = None
    if _state.memory_enabled and MNEMOSYNE_AVAILABLE:
        try:
            results = recall(query=user_message, top_k=3)
            if results:
                past_patterns = [
                    {"goal_type": r.get("metadata", {}).get("goal_type", "?"), "count": 1}
                    for r in results
                    if r.get("metadata", {}).get("source") == "meboya_goal"
                ]
        except Exception:
            logger.debug("meboya memory recall failed", exc_info=True)

    guidance = build_goal_prompt(
        user_message=user_message,
        depth=depth,
        past_patterns=past_patterns,
        hats_enabled=_state.hats_enabled,
    )

    _state.depth = depth
    return {"context": guidance}


# ---------------------------------------------------------------------------
# Hook: post_llm_call (formatting + memory)
# ---------------------------------------------------------------------------


async def on_post_llm_call(
    response_text: str = "",
    **_: Any,
) -> Optional[str]:
    """Format response and save goal pattern to memory."""
    if not _state.enabled or not response_text:
        return None

    active_hats = detect_active_hats(response_text)
    _state._active_hats = active_hats

    if _state.memory_enabled and MNEMOSYNE_AVAILABLE and _state._current_user_message:
        try:
            goal_type = extract_goal_from_response(response_text)
            if goal_type != "unknown":
                remember(
                    content=_state._current_user_message,
                    importance=0.7,
                    source="meboya_goal",
                    metadata={"goal_type": goal_type, "depth": _state.depth},
                )
        except Exception:
            logger.debug("meboya memory save failed", exc_info=True)

    formatted = format_response(
        response_text,
        show_simulation=_state.show_simulation,
        active_hats=active_hats,
    )
    return formatted if formatted != response_text else None


# ---------------------------------------------------------------------------
# Hook: post_tool_call (track recursion)
# ---------------------------------------------------------------------------


async def on_post_tool_call(
    tool_name: str = "",
    args: Optional[Dict[str, Any]] = None,
    result: Any = None,
    **_: Any,
) -> None:
    """Track simulate/reason_deeper usage."""
    if tool_name == "simulate" and isinstance(result, str):
        logger.debug("meboya simulate called, result_len=%d", len(result))
    elif tool_name == "reason_deeper" and isinstance(args, dict):
        _state._recursion_depth += 1
        _state._reasoning_stack.append(
            {"level": _state._recursion_depth, "focus": args.get("focus", "")}
        )
        logger.debug(
            "meboya reason_deeper called (level %d/%d, focus=%s)",
            _state._recursion_depth,
            _state.max_recursion,
            args.get("focus", ""),
        )


# ---------------------------------------------------------------------------
# Slash Commands
# ---------------------------------------------------------------------------


COMMAND_HELP = """
**Meboya Commands** (mirrors DOGA):
- `/meboya on` — Enable auto-thinking
- `/meboya off` — Disable
- `/meboya status` — Show current config
- `/meboya depth <1-5>` — Set fixed depth (disables auto)
- `/meboya auto` — Enable auto-depth
- `/meboya hats on|off` — Toggle De Bono hats
- `/meboya sim on|off` — Toggle simulation summary display
- `/meboya memory on|off` — Toggle Mnemosyne goal memory
- `/meboya max-recursion <1-5>` — Set max recursive reasoning depth
- `/meboya test <message>` — Test thinking injection for a message
"""


def handle_meboya_command(cmd: str) -> str:
    """Parse and execute /meboya slash command."""
    logger.info("meboya command handler called with: %r", cmd)

    raw = cmd.strip()
    # Strip command prefix if present (Hermes may pass "/meboya ..." or just "...")
    for prefix in ("/meboya ", "/doga "):
        if raw.lower().startswith(prefix):
            raw = raw[len(prefix):].strip()
            break
    # Also strip bare "/meboya" or "/doga" with no args
    if raw.lower() in ("/meboya", "/doga"):
        raw = ""

    parts = raw.split()
    if not parts:
        return _meboya_status_str()

    sub = parts[0].lower()

    if sub == "on":
        _state.enabled = True
        return "✅ Meboya enabled"
    elif sub == "off":
        _state.enabled = False
        return "⏸️  Meboya disabled"
    elif sub == "status":
        return _meboya_status_str()
    elif sub == "depth" and len(parts) >= 2:
        try:
            d = int(parts[1])
            if 1 <= d <= 5:
                _state.depth = d
                _state.auto_depth = False
                return f"📏 Depth set to {d} (auto disabled)"
        except ValueError:
            pass
        return "Usage: /meboya depth <1-5>"
    elif sub == "auto":
        _state.auto_depth = True
        return "🔄 Auto-depth enabled"
    elif sub == "hats" and len(parts) >= 2:
        _state.hats_enabled = parts[1].lower() == "on"
        return f"🎩 Hats {'enabled' if _state.hats_enabled else 'disabled'}"
    elif sub == "sim" and len(parts) >= 2:
        _state.show_simulation = parts[1].lower() == "on"
        return f"📊 Simulation display {'enabled' if _state.show_simulation else 'disabled'}"
    elif sub == "memory" and len(parts) >= 2:
        _state.memory_enabled = parts[1].lower() == "on"
        return f"🧠 Memory {'enabled' if _state.memory_enabled else 'disabled'}"
    elif sub == "max-recursion" and len(parts) >= 2:
        try:
            mr = int(parts[1])
            if 1 <= mr <= 5:
                _state.max_recursion = mr
                return f"🔁 Max recursion set to {mr}"
        except ValueError:
            pass
        return "Usage: /meboya max-recursion <1-5>"
    elif sub == "test" and len(parts) >= 2:
        test_msg = " ".join(parts[1:])
        complexity = assess_complexity(test_msg)
        depth = depth_from_complexity(complexity) if _state.auto_depth else _state.depth
        guidance = build_goal_prompt(test_msg, depth=depth, hats_enabled=_state.hats_enabled)
        return f"**Test Injection** (complexity={complexity}, depth={depth}):\n\n{guidance}"
    elif sub == "health":
        return _meboya_health_str()

    return COMMAND_HELP


def _meboya_status_str() -> str:
    """Format and return current status."""
    return f"""**Meboya Status**
Enabled: {_state.enabled}
Auto-depth: {_state.auto_depth} (fixed: {_state.depth})
Hats: {_state.hats_enabled}
Simulation display: {_state.show_simulation}
Memory: {_state.memory_enabled}
Max recursion: {_state.max_recursion}
Mnemosyne: {'available' if MNEMOSYNE_AVAILABLE else 'not installed'}"""


def _meboya_health_str() -> str:
    """Runtime observability dump."""
    import time
    return f"""**Meboya Health Dashboard**

Runtime State:
  Current depth: {_state.depth}
  Current user msg: "{_state._current_user_message[:80]}{'...' if len(_state._current_user_message) > 80 else ''}"
  Active hats: {', '.join(_state._active_hats) if _state._active_hats else 'none'}
  Recursion depth: {_state._recursion_depth} / {_state.max_recursion}
  Reasoning stack: {len(_state._reasoning_stack)} frames
  Stop sent: {_state._stop_sent}

Feature Flags:
  Auto-depth: {_state.auto_depth}
  Hats enabled: {_state.hats_enabled}
  Sim display: {_state.show_simulation}
  Memory: {_state.memory_enabled}

Memory Backend:
  Mnemosyne available: {MNEMOSYNE_AVAILABLE}

Engine:
  MonteCarlo thread-local RNG: {'initialized' if hasattr(_engine._local, 'rng') else 'cold'}
"""


# ---------------------------------------------------------------------------
# Plugin Registration
# ---------------------------------------------------------------------------


def register(ctx: Any) -> None:
    """Register hooks, tools, and commands with Hermes."""
    ctx.register_hook("pre_llm_call", on_pre_llm_call)
    ctx.register_hook("post_llm_call", on_post_llm_call)
    ctx.register_hook("post_tool_call", on_post_tool_call)

    ctx.register_tool("simulate", "meboya", SIMULATE_SCHEMA, simulate_tool_handler)
    ctx.register_tool("reason_deeper", "meboya", REASON_DEEPER_SCHEMA, reason_deeper_tool_handler)

    # Slash commands (in-session /meboya, not hermes subcommand)
    ctx.register_command(
        "meboya",
        handle_meboya_command,
        description="Meboya auto-thinking control",
        args_hint="on|off|status|depth <1-5>|auto|hats on|off|sim on|off|memory on|off|max-recursion <1-5>|test <message>",
    )
    ctx.register_command(
        "doga",
        handle_meboya_command,
        description="Alias for /meboya (DOGA compat)",
        args_hint="on|off|status",
    )

    logger.info("Meboya plugin registered (DOGA parity + Verification + Boundary)")


def _register_doga_alias(ctx: Any) -> None:
    ctx.register_cli_command("doga", handle_meboya_command, "Alias for /meboya (DOGA compat)")


__all__ = ["register", "handle_meboya_command", "MNEMOSYNE_AVAILABLE"]