"""
Resolve which execute path to take: Safe Cron, script archive, or NL→Bash.

Primary: LLM classification (when API key is configured).
Fallback: keyword/regex intents from intents.py (spellings, offline).
Safety: destructive cron phrases from regex always block before/after LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from .intents import (
    detect_archive_intent,
    detect_safe_cron_intent,
    extract_cron_expression,
    extract_list_calendar_day,
    extract_script_name,
    is_minimal_filename_only,
    is_safe_cron_expr,
)

if TYPE_CHECKING:
    from .llm_client import LLMClient


@dataclass
class ResolvedExecuteRoute:
    """Unified routing result for POST /api/execute."""

    cron_blocked: bool = False
    archive_forbidden: bool = False
    cron_action: Optional[str] = None  # 'list' | 'schedule'
    archive_action: Optional[str] = None  # 'list' | 'rerun' | 'explain'
    script_name: Optional[str] = None
    cron_expr: Optional[str] = None
    date_scope: str = "all"
    list_day_start: Optional[str] = None
    execution_style: str = "auto"  # 'auto' | 'single' | 'multi'
    source: str = "regex"  # 'llm' | 'regex' | 'llm+regex'


# LLM classifier can misread bare filenames (e.g. dana.txt) as "list archive scripts".
_LLM_WORKFLOW_ROUTES = frozenset({
    "cron_list",
    "cron_schedule",
    "archive_list",
    "archive_rerun",
    "archive_explain",
})


def _llm_workflow_route_trusted(nl: str, route: str, arc_r: dict, cron_r: dict) -> bool:
    """
    Allow LLM cron/archive routes only when local regex agrees, except forbidden routes.
    Bare filenames never trigger archive/cron workflows from the LLM alone.
    """
    if route not in _LLM_WORKFLOW_ROUTES:
        return True
    if is_minimal_filename_only(nl):
        return False
    if route == "cron_list":
        return cron_r.get("action") == "list"
    if route == "cron_schedule":
        return cron_r.get("action") == "schedule"
    if route == "archive_list":
        return arc_r.get("action") == "list"
    if route == "archive_rerun":
        return arc_r.get("action") == "rerun"
    if route == "archive_explain":
        return arc_r.get("action") == "explain"
    return False


def resolve_execute_route(natural_language: str, llm_client: "LLMClient") -> ResolvedExecuteRoute:
    nl = (natural_language or "").strip()
    cron_r = detect_safe_cron_intent(nl)
    arc_r = detect_archive_intent(nl)

    # Hard stop: substring rules catch obvious destructive wording regardless of LLM
    if cron_r.get("action") == "blocked_remove":
        return ResolvedExecuteRoute(cron_blocked=True, source="regex")

    llm = None
    if getattr(llm_client, "api_key", None):
        llm = llm_client.classify_execution_route(nl)

    if llm and llm.get("success"):
        route = (llm.get("route") or "unclear").strip().lower()
        src = "llm"

        if route == "cron_forbidden":
            return ResolvedExecuteRoute(cron_blocked=True, source=src)

        if route == "archive_forbidden":
            return ResolvedExecuteRoute(archive_forbidden=True, source=src)

        if not _llm_workflow_route_trusted(nl, route, arc_r, cron_r):
            route = "unclear"
        else:
            script_name = _norm_script(llm.get("script_name")) or extract_script_name(nl)
            cron_expr = _norm_cron(llm.get("cron_expression")) or extract_cron_expression(nl)

        if route == "unclear":
            pass
        elif route == "cron_list":
            return ResolvedExecuteRoute(cron_action="list", source=src)

        elif route == "cron_schedule":
            return ResolvedExecuteRoute(
                cron_action="schedule",
                script_name=script_name,
                cron_expr=cron_expr,
                source=src,
            )

        elif route == "archive_list":
            ds, day = _date_scope_from_llm(llm, arc_r, nl)
            return ResolvedExecuteRoute(
                archive_action="list",
                date_scope=ds,
                list_day_start=day,
                script_name=script_name,
                source=src,
            )

        elif route == "archive_rerun":
            return ResolvedExecuteRoute(
                archive_action="rerun",
                script_name=script_name,
                source=src,
            )

        elif route == "archive_explain":
            return ResolvedExecuteRoute(
                archive_action="explain",
                script_name=script_name,
                source=src,
            )

        elif route == "script_command":
            return ResolvedExecuteRoute(execution_style="multi", source=src)

        elif route == "normal_command":
            return ResolvedExecuteRoute(execution_style="single", source=src)

        # unclear (or unknown route) → fall through to regex merge below

    # Regex-only or LLM unclear: legacy detectors
    if cron_r.get("action") == "list":
        return ResolvedExecuteRoute(cron_action="list", source="regex")

    if cron_r.get("action") == "schedule":
        return ResolvedExecuteRoute(
            cron_action="schedule",
            script_name=cron_r.get("script_name") or extract_script_name(nl),
            cron_expr=cron_r.get("cron_expr") or extract_cron_expression(nl),
            source="regex",
        )

    if arc_r.get("action") == "list":
        ds = arc_r.get("date_scope") or "all"
        day = extract_list_calendar_day(nl) if ds == "day" else None
        return ResolvedExecuteRoute(
            archive_action="list",
            date_scope=ds,
            list_day_start=arc_r.get("list_day_start") or day,
            source="regex",
        )

    if arc_r.get("action") == "rerun":
        return ResolvedExecuteRoute(
            archive_action="rerun",
            script_name=arc_r.get("script_name") or extract_script_name(nl),
            source="regex",
        )

    if arc_r.get("action") == "explain":
        return ResolvedExecuteRoute(
            archive_action="explain",
            script_name=arc_r.get("script_name") or extract_script_name(nl),
            source="regex",
        )

    # Default: NL → Bash (style auto unless LLM already set execution_style)
    if llm and llm.get("success"):
        es = llm.get("execution_style") or "auto"
        if es in ("single", "multi"):
            return ResolvedExecuteRoute(execution_style=es, source="llm")

    return ResolvedExecuteRoute(execution_style="auto", source="regex")


def _norm_script(name) -> Optional[str]:
    if not name or not isinstance(name, str):
        return None
    s = name.strip()
    return s if s else None


def _norm_cron(expr) -> Optional[str]:
    if not expr or not isinstance(expr, str):
        return None
    s = expr.strip()
    return s if s else None


def _date_scope_from_llm(llm: dict, arc_r: dict, nl: str):
    """Validate date_scope from classifier; fall back to regex helpers."""
    raw = (llm.get("date_scope") or "").strip().lower()
    allowed = ("all", "today", "yesterday", "day")
    if raw in allowed:
        scope = raw
    else:
        scope = arc_r.get("date_scope") or "all"
    day = llm.get("calendar_day")
    if isinstance(day, str) and day.strip():
        day = day.strip()
    else:
        day = None
    if scope == "day" and not day:
        day = extract_list_calendar_day(nl)
    if scope not in allowed:
        scope = "all"
    return scope, day


def validate_schedule_inputs(script_name: Optional[str], cron_expr: Optional[str]) -> tuple[bool, str]:
    """Shared checks before SSH schedule (expression + basename)."""
    if not script_name or not script_name.endswith(".sh"):
        return False, "Need a safe .sh script name from the request."
    if not cron_expr:
        return False, "Need a cron expression or macro (e.g. @daily)."
    if not is_safe_cron_expr(cron_expr):
        return False, "Cron expression is not in an allowed format."
    return True, ""
