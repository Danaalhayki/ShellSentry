"""
Build human-readable summaries and structured text reports for execution results.
"""

import re
from typing import Any, Dict, List, Optional

# IPv4 (simple validation via regex; filter loopback / zero later)
_IPV4 = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
)


def _line_count(text: Optional[str]) -> int:
    if not text or not str(text).strip():
        return 0
    return len(str(text).strip().splitlines())


def _truncate(s: str, max_len: int = 120) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _plain_error_hint(err: str) -> str:
    """Turn common technical errors into short, plain language (best effort)."""
    e = (err or "").strip()
    if len(e) > 200:
        e = e[:199] + "…"
    low = e.lower()
    if "authentication failed" in low or ("password" in low and "denied" in low):
        return "Signing in to that computer did not work. Check the username and password or SSH key."
    if "timeout" in low or "timed out" in low:
        return "The computer did not answer in time. It may be busy or unreachable."
    if "could not resolve" in low or "name resolution" in low or "nodename nor servname" in low:
        return "The address name could not be looked up. Check spelling and network."
    if "port 22" in low or "connection refused" in low or "no route to host" in low:
        return "We could not reach that computer on the network. It may be off or blocking connections."
    if "permission denied" in low:
        return "You are not allowed to do that on that computer."
    return e


def _unique_ipv4s(text: str) -> List[str]:
    """Collect unique IPv4 addresses from text, skipping loopback and 0.0.0.0."""
    seen: set = set()
    out: List[str] = []
    for m in _IPV4.finditer(text or ""):
        s = m.group(0)
        if s.startswith("127.") or s == "0.0.0.0":
            continue
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _wants_ip_question(request: str, cmd: str) -> bool:
    low = (request or "").lower()
    cmd_low = (cmd or "").lower()
    if "ping" in low and not any(
        p in low for p in ("ip address", "ip addr", "show ip", "network interface", "ifconfig")
    ):
        return False
    request_phrases = (
        "ip address",
        "ip addr",
        "network address",
        "interfaces",
        "interface",
        "ifconfig",
        "show ip",
        "local ip",
        "ipv4",
        "ethernet",
        "wlan",
        "wifi address",
        "what is my ip",
    )
    if any(p in low for p in request_phrases):
        return True
    if re.search(r"\bip\s+a\b", cmd_low) or "ip addr" in cmd_low or "ip address" in cmd_low:
        return True
    cmd_hints = ("ifconfig", "hostname -i", "hostname -I", "ip -br")
    return any(x in cmd_low for x in cmd_hints)


def _wants_ping_question(request: str, cmd: str) -> bool:
    low = (request or "").lower()
    return "ping" in low or (cmd or "").strip().lower().startswith("ping ")


def _wants_uptime_question(request: str, cmd: str) -> bool:
    low = (request or "").lower()
    cmd_low = (cmd or "").lower()
    return any(x in low for x in ("uptime", "how long", "running since", "boot time")) or "uptime" in cmd_low


def _wants_disk_question(request: str, cmd: str) -> bool:
    low = (request or "").lower()
    cmd_low = (cmd or "").lower()
    return any(x in low for x in ("disk", "space", "storage", "filesystem", "free space", "df ")) or (
        "df " in cmd_low or cmd_low.strip() == "df" or cmd_low.startswith("df -")
    )


def _try_readable_answer_from_output(
    original_request: str,
    generated_command: str,
    results: Dict[str, Any],
) -> Optional[str]:
    """
    Turn successful stdout into one or two plain sentences (e.g. 'The IP address is …').
    Returns None if we cannot confidently summarize.
    """
    ok_items = [(h, r) for h, r in results.items() if r.get("success")]
    if not ok_items:
        return None

    req = original_request or ""
    cmd = generated_command or ""

    # --- IP / interfaces ---
    if _wants_ip_question(req, cmd):
        chunks: List[str] = []
        for host, r in ok_items:
            out = r.get("stdout") or ""
            ips = _unique_ipv4s(out)
            if not ips:
                continue
            if len(ips) == 1:
                if host.strip() == ips[0]:
                    chunks.append(f"This computer's IP address is {ips[0]}.")
                else:
                    chunks.append(f"On {host}, the IP address is {ips[0]}.")
            else:
                if len(ips) == 2:
                    chunks.append(f"On {host}, the IP addresses are {ips[0]} and {ips[1]}.")
                else:
                    joined = ", ".join(ips[:-1]) + f", and {ips[-1]}"
                    chunks.append(f"On {host}, the IP addresses are {joined}.")
        if chunks:
            return " ".join(chunks)

    # --- Ping ---
    if _wants_ping_question(req, cmd):
        chunks = []
        for host, r in ok_items:
            out = (r.get("stdout") or "") + "\n" + (r.get("stderr") or "")
            low = out.lower()
            if "0 received" in low or "100% packet loss" in low:
                chunks.append(f"The ping from {host} did not get a reply (host may be down or blocking pings).")
            elif "1 received" in low or "0% packet loss" in low or "bytes from" in low:
                # Try to pull round-trip time
                m = re.search(r"time[=<]([0-9.]+)\s*ms", out, re.I)
                if m:
                    chunks.append(f"The ping to the target from {host} succeeded (about {m.group(1)} ms round trip).")
                else:
                    chunks.append(f"The ping from {host} succeeded; the host answered.")
        if chunks:
            return " ".join(chunks)

    # --- Uptime ---
    if _wants_uptime_question(req, cmd):
        chunks = []
        for host, r in ok_items:
            line = (r.get("stdout") or "").strip().splitlines()
            if line:
                chunks.append(f"On {host}, uptime looks like this: {line[0].strip()}")
        if chunks:
            return " ".join(chunks) + "."

    # --- Disk (first useful line of df) ---
    if _wants_disk_question(req, cmd):
        chunks = []
        for host, r in ok_items:
            lines = [ln.strip() for ln in (r.get("stdout") or "").splitlines() if ln.strip()]
            data_line = None
            for i, ln in enumerate(lines):
                if ln.lower().startswith("filesystem") and i + 1 < len(lines):
                    data_line = lines[i + 1]
                    break
            if data_line is None and lines:
                data_line = lines[0]
            if data_line:
                chunks.append(
                    f"On {host}, disk usage includes this line: {data_line} "
                    f"(see the full report for the complete table)."
                )
        if chunks:
            return " ".join(chunks)

    return None


def build_natural_language_summary(
    original_request: str,
    generated_command: str,
    results: Dict[str, Any],
    host_context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Short, plain-language explanation for people who are not technical.
    Technical detail belongs in the formatted report only.
    (generated_command and host_context are passed through for API compatibility;
    command and probe details appear in the report, not here.)
    """
    req = (original_request or "").strip()
    req_display = _truncate(req, 260)

    if not results:
        return (
            f'You asked: "{req_display}". '
            "We did not receive a result from the servers. See the full report below if it has more to say."
        )

    servers = list(results.keys())
    n = len(servers)
    ok_hosts = [h for h in servers if results[h].get("success")]
    bad_hosts = [h for h in servers if not results[h].get("success")]

    parts: list[str] = []
    parts.append(f'You asked: "{req_display}".')

    readable = _try_readable_answer_from_output(req, generated_command or "", results)

    if n == 1:
        h = servers[0]
        r = results[h]
        if r.get("success"):
            if readable:
                parts.append(readable)
                parts.append("You can open the full report below to see the full text from the computer.")
            else:
                parts.append(
                    f"It finished successfully on {h}. "
                    "Open the full report below to read the detailed answer from that computer."
                )
        else:
            err = r.get("error") or r.get("stderr") or "Something went wrong."
            parts.append(f"It did not work on {h}. {_plain_error_hint(str(err))}")
    else:
        if readable and ok_hosts:
            parts.append(readable)
            parts.append("You can open the full report below for the complete output from each computer.")
        elif not bad_hosts:
            if not readable:
                parts.append(
                    f"It worked on all {n} computers. The full report below has the details for each one."
                )
        elif not ok_hosts:
            parts.append(
                f"We tried all {n} computers, but none of them finished successfully."
            )
        else:
            if not readable:
                parts.append(
                    f"We tried {n} computers: {len(ok_hosts)} went fine and {len(bad_hosts)} had a problem."
                )
        for h in bad_hosts[:4]:
            r = results[h]
            err = r.get("error") or r.get("stderr") or "Unknown issue."
            parts.append(f"{h}: {_plain_error_hint(str(err))}")
        if len(bad_hosts) > 4:
            parts.append(f"Other computers also had issues; names are in the full report below.")

    return " ".join(parts)


def build_formatted_report(
    original_request: str,
    generated_command: str,
    results: Dict[str, Any],
    host_context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Multi-section plain-text report suitable for display in a monospace block or logs.
    """
    lines: list[str] = []
    w = 72

    def hr(char: str = "=") -> None:
        lines.append(char * w)

    hr("=")
    lines.append("SHELLSENTRY EXECUTION REPORT".center(w))
    hr("=")
    lines.append("")

    lines.append("YOUR REQUEST")
    hr("-")
    lines.append((original_request or "").strip() or "(empty)")
    lines.append("")

    lines.append("GENERATED COMMAND")
    hr("-")
    lines.append((generated_command or "").strip() or "(none)")
    lines.append("")

    if not results:
        lines.append("PER-SERVER RESULTS")
        hr("-")
        lines.append("(no results)")
        lines.append("")
        return "\n".join(lines)

    ok_n = sum(1 for r in results.values() if r.get("success"))
    lines.append("OVERVIEW")
    hr("-")
    lines.append(f"Servers: {len(results)}  |  Succeeded: {ok_n}  |  Failed: {len(results) - ok_n}")
    lines.append("")

    if host_context:
        lines.append("HOST CONTEXT (PRE-RUN PROBE)")
        hr("-")
        for host in results.keys():
            ctx = host_context.get(host)
            if isinstance(ctx, dict):
                uname = ctx.get("uname_line") or "(no uname)"
                lines.append(f"[{host}]")
                lines.append(f"  OS: {_truncate(str(uname), w - 4)}")
            else:
                lines.append(f"[{host}] (probe unavailable)")
        lines.append("")

    lines.append("PER-SERVER RESULTS")
    hr("-")
    for host, r in results.items():
        ok = r.get("success", False)
        ec = r.get("exit_code")
        status = "SUCCESS" if ok else "FAILED"
        lines.append(f"▸ {host}  —  {status}  (exit {ec})")
        if r.get("error"):
            lines.append(f"  Error: {r['error']}")
        out = r.get("stdout") or ""
        err = r.get("stderr") or ""
        lines.append(f"  stdout: {_line_count(out)} line(s), stderr: {_line_count(err)} line(s)")
        if out.strip():
            preview = "\n".join(out.strip().splitlines()[:12])
            if _line_count(out) > 12:
                preview += "\n  … (output continues; truncated here)"
            lines.append("  --- stdout preview ---")
            for pl in preview.splitlines():
                lines.append(f"  {pl}")
        if err.strip() and not ok:
            elines = err.strip().splitlines()[:8]
            lines.append("  --- stderr ---")
            for el in elines:
                lines.append(f"  {el}")
        lines.append("")

    hr("=")
    lines.append("END OF REPORT".center(w))
    hr("=")

    return "\n".join(lines)


def format_execution_payload(
    original_request: str,
    generated_command: str,
    results: Dict[str, Any],
    host_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Return strings to merge into the JSON API response."""
    return {
        "natural_language_summary": build_natural_language_summary(
            original_request, generated_command, results, host_context
        ),
        "formatted_report": build_formatted_report(
            original_request, generated_command, results, host_context
        ),
    }


def format_error_summary(
    error_title: str,
    reason: Optional[str] = None,
    details: Optional[str] = None,
) -> str:
    """Plain-language lines for the dashboard and API when something stops before a normal result."""
    head = (error_title or "").strip()
    if head and not head.endswith((".", "!", "?")):
        head += "."
    parts = [head] if head else []
    if reason:
        parts.append(f"Here's why: {reason}")
    if details:
        parts.append(f"You can try: {details}")
    return " ".join(parts)
