"""Natural-language intent helpers for archive scripts and safe cron.

Keyword lists and regex patterns load from config/intents.json (merge over defaults).
Override path with env INTENTS_CONFIG_PATH.
"""

from __future__ import annotations

import copy
import json
import os
import re
from datetime import date as date_type
from pathlib import Path
from typing import Any, Dict, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_FILE = _PROJECT_ROOT / 'config' / 'intents.json'


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, val in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


def _built_in_defaults() -> Dict[str, Any]:
    return {
        'unicode_dash_chars': [
            '\u2010', '\u2011', '\u2012', '\u2013', '\u2014', '\u2212',
        ],
        'archive': {
            'script_words': ['script', 'scripts'],
            'archive_hints': [
                'shellsentryscripts', 'saved script', 'saved scripts',
            ],
            'list_words': ['list', 'show', 'display', 'ls'],
            'run_phrases': [
                'rerun', 're-run', 're run',
                'reexecute', 're-execute', 're execute',
                'run again', 'execute saved',
            ],
            'explain_phrases': ['explain', 'what does'],
            'scope_yesterday_words': ['yesterday'],
            'scope_today_words': ['today'],
        },
        'cron': {
            'cron_words': ['cron', 'crontab', 'schedule', 'scheduled'],
            'blocked_remove_phrases': [
                'delete cron', 'remove cron', 'clear crontab', 'wipe crontab',
            ],
            'list_phrases': [
                'list cron', 'show cron', 'display cron', 'show crontab',
            ],
        },
        'patterns': {
            'script_filename_regex': r'\b([A-Za-z0-9._-]+\.sh)\b',
            'cron_macro_regex': (
                r'\b(@reboot|@yearly|@annually|@monthly|@weekly|@daily|@midnight|@hourly)\b'
            ),
            'cron_five_field_regex': (
                r'([A-Za-z0-9*/,\-]+)\s+([A-Za-z0-9*/,\-]+)\s+([A-Za-z0-9*/,\-]+)\s+'
                r'([A-Za-z0-9*/,\-]+)\s+([A-Za-z0-9*/,\-]+)'
            ),
            'cron_expression_cues': [r'cron expression\s*', r'with\s*'],
            'cron_macro_allowlist_regex': (
                r'@(reboot|yearly|annually|monthly|weekly|daily|midnight|hourly)'
            ),
            'cron_token_regex': r'^[A-Za-z0-9*/,\-]+$',
        },
    }


def load_intents_config() -> Dict[str, Any]:
    cfg = _built_in_defaults()
    path = os.environ.get('INTENTS_CONFIG_PATH', '').strip()
    config_path = Path(path) if path else _DEFAULT_FILE
    if config_path.is_file():
        with open(config_path, encoding='utf-8') as f:
            cfg = _deep_merge(cfg, json.load(f))
    return cfg


_INTENTS = load_intents_config()


def reload_intents_config() -> None:
    """Reload JSON config (e.g. after tests patch env path)."""
    global _INTENTS
    _INTENTS = load_intents_config()


def normalize_intent_text(text):
    """
    Normalize punctuation/spacing so intent matching works with unicode dashes
    like Re‑execute / Re–execute / Re—execute.
    """
    if not text:
        return ''
    normalized = str(text)
    for ch in _INTENTS.get('unicode_dash_chars') or []:
        normalized = normalized.replace(ch, '-')
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def safe_text_for_log(text):
    """Prevent Windows cp1252 console logger crashes on non-encodable chars."""
    if not text:
        return ''
    try:
        return str(text).encode('cp1252', errors='replace').decode('cp1252')
    except Exception:
        return str(text).encode('ascii', errors='replace').decode('ascii')


def extract_script_name(text):
    """Extract archive script filename from user request."""
    if not text:
        return None
    pat = (_INTENTS.get('patterns') or {}).get('script_filename_regex') or (
        r'\b([A-Za-z0-9._-]+\.sh)\b'
    )
    m = re.search(pat, text)
    return m.group(1) if m else None


def _valid_ymd(year: int, month: int, day: int) -> bool:
    try:
        date_type(year, month, day)
        return True
    except ValueError:
        return False


def extract_list_calendar_day(text: Optional[str]) -> Optional[str]:
    """
    Find an explicit calendar day in user text for filtering saved-script listings.
    Returns YYYY-MM-DD or None.

    - ISO YYYY-MM-DD (or YYYY-M-D) is matched first.
    - Same-delimiter triplets: with '-' use day-month-year; with '/' use month/day/year (US).
    """
    if not text:
        return None
    t = normalize_intent_text(text)

    for m in re.finditer(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', t):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if _valid_ymd(y, mo, d):
            return f'{y:04d}-{mo:02d}-{d:02d}'

    for m in re.finditer(r'\b(\d{1,2})([/-])(\d{1,2})\2(\d{4})\b', t):
        a, sep, b, y = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))
        if sep == '-':
            day, month = a, b
        else:
            month, day = a, b
        if _valid_ymd(y, month, day):
            return f'{y:04d}-{month:02d}-{day:02d}'
    return None


def detect_archive_intent(text):
    """
    Detect explicit script-archive actions from natural language.
    Returns dict with action/list scope/script_name.
    """
    arc = _INTENTS.get('archive') or {}

    normalized_text = normalize_intent_text(text)
    low = normalized_text.lower()

    script_words = arc.get('script_words') or ()
    archive_hints = arc.get('archive_hints') or ()
    list_words = arc.get('list_words') or ()
    run_phrases = arc.get('run_phrases') or ()
    explain_phrases = arc.get('explain_phrases') or ()
    yesterday_words = arc.get('scope_yesterday_words') or ()
    today_words = arc.get('scope_today_words') or ()

    def _any_substring(haystack: str, needles):
        return any(n in haystack for n in needles)

    has_script_word = _any_substring(low, script_words)
    archive_hint = _any_substring(low, archive_hints)
    wants_list = _any_substring(low, list_words)
    wants_run = _any_substring(low, run_phrases)
    wants_explain = _any_substring(low, explain_phrases)

    script_name = extract_script_name(normalized_text)

    if wants_run and script_name:
        return {'action': 'rerun', 'script_name': script_name}
    if wants_explain and script_name:
        return {'action': 'explain', 'script_name': script_name}

    if not has_script_word and not archive_hint:
        return {'action': None}

    if wants_list:
        scope = 'all'
        if _any_substring(low, yesterday_words):
            scope = 'yesterday'
        elif _any_substring(low, today_words):
            scope = 'today'
        return {'action': 'list', 'date_scope': scope}
    return {'action': None}


def extract_cron_expression(text):
    """Extract a cron expression (5-field or @daily style) from request text."""
    if not text:
        return None
    pats = _INTENTS.get('patterns') or {}
    macro_re = pats.get('cron_macro_regex') or (
        r'\b(@reboot|@yearly|@annually|@monthly|@weekly|@daily|@midnight|@hourly)\b'
    )
    cron_5 = pats.get('cron_five_field_regex') or (
        r'([A-Za-z0-9*/,\-]+)\s+([A-Za-z0-9*/,\-]+)\s+([A-Za-z0-9*/,\-]+)\s+'
        r'([A-Za-z0-9*/,\-]+)\s+([A-Za-z0-9*/,\-]+)'
    )
    cues = pats.get('cron_expression_cues') or [r'cron expression\s*', r'with\s*']

    t = normalize_intent_text(text)
    macro = re.search(macro_re, t, re.IGNORECASE)
    if macro:
        return macro.group(1).lower()

    for cue in cues:
        m = re.search(cue + cron_5, t, re.IGNORECASE)
        if m:
            return ' '.join(m.groups()).strip()

    matches = re.findall(cron_5, t, re.IGNORECASE)
    if not matches:
        return None
    return ' '.join(matches[-1]).strip()


def is_safe_cron_expr(expr):
    """Basic cron expression validation with strict character allowlist."""
    if not expr:
        return False
    pats = _INTENTS.get('patterns') or {}
    macro_full = pats.get('cron_macro_allowlist_regex') or (
        r'@(reboot|yearly|annually|monthly|weekly|daily|midnight|hourly)'
    )
    token_re_str = pats.get('cron_token_regex') or r'^[A-Za-z0-9*/,\-]+$'

    e = expr.strip()
    if re.fullmatch(macro_full, e, re.IGNORECASE):
        return True
    parts = e.split()
    if len(parts) != 5:
        return False
    token_re = re.compile(token_re_str)
    return all(token_re.fullmatch(p) is not None for p in parts)


def detect_safe_cron_intent(text):
    """Detect safe cron actions for managed archived scripts."""
    cron_cfg = _INTENTS.get('cron') or {}

    normalized_text = normalize_intent_text(text)
    low = normalized_text.lower()

    cron_words = cron_cfg.get('cron_words') or ()
    blocked = cron_cfg.get('blocked_remove_phrases') or ()
    list_phrases = cron_cfg.get('list_phrases') or ()

    if not any(k in low for k in cron_words):
        return {'action': None}

    if any(k in low for k in blocked):
        return {'action': 'blocked_remove'}

    if any(k in low for k in list_phrases):
        return {'action': 'list'}

    script_name = extract_script_name(normalized_text)
    cron_expr = extract_cron_expression(normalized_text)
    if script_name and cron_expr:
        return {'action': 'schedule', 'script_name': script_name, 'cron_expr': cron_expr}
    return {'action': None}
