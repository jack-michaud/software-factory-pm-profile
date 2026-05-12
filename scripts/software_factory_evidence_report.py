#!/usr/bin/env python3
"""Generate Software Factory PM evidence reports from public Kanban surfaces.

Boundary: this script reads only explicit Kanban CLI/API JSON output or a caller-
provided public-safe JSON export. It must not read raw SQLite databases, .env,
auth.json, sessions, memories, logs, local profile state, private notes, SSH keys,
OAuth tokens, API keys, or sprite credentials.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPORT_VERSION = "sf_visibility.v1"
PRIVATE_TOKENS = (
    ".env",
    "auth.json",
    "state.db",
    "kanban.db",
    "sessions",
    "memories",
    "logs",
    "local profile state",
    "private obsidian",
    "api key",
    "oauth token",
    "ssh key",
    "sprite credential",
)
ROLE_BY_ASSIGNEE = {
    "pm": "pm",
    "orchestrator": "pm",
    "builder": "builder",
    "reviewer": "reviewer",
    "publisher": "publisher",
    "docs": "docs",
    "installer": "installer",
}
ROLE_REQUIRED_EVIDENCE = {
    "builder": ["repo_url", "local_worktree", "branch", "commit", "diff_stat", "changed_files", "validation"],
    "reviewer": ["outcome", "coverage", "findings", "review_subject_task_ids"],
    "publisher": ["publication_target", "published_refs", "post_publish_validation"],
    "installer": ["install_targets_verified", "post_publish_validation"],
    "pm": ["decision_record", "source_map", "task_graph"],
}
EVIDENCE_KIND_BY_KEY = {
    "repo_url": "url",
    "local_worktree": "artifact",
    "branch": "branch",
    "commit": "commit",
    "commits": "commit",
    "diff_stat": "diff",
    "changed_files": "artifact",
    "validation": "validation",
    "validation_output": "validation",
    "artifacts": "artifact",
    "artifact": "artifact",
    "published_refs": "commit",
    "publication_target": "artifact",
    "install_targets_verified": "artifact",
    "runtime_evidence": "checkpoint",
    "source_map": "artifact",
    "decision_record": "approval",
    "outcome": "review",
    "coverage": "review",
    "findings": "review",
}


def iso(ts: Any) -> Optional[str]:
    if ts is None or ts == "":
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except Exception:
        return str(ts)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def task_role(task: Dict[str, Any], runs: Optional[List[Dict[str, Any]]] = None) -> str:
    text = " ".join(str(x or "") for x in [task.get("assignee"), task.get("title"), task.get("body")]).lower()
    for token, role in ROLE_BY_ASSIGNEE.items():
        if token in text:
            return role
    if runs:
        for run in runs:
            profile = str(run.get("profile") or "").lower()
            for token, role in ROLE_BY_ASSIGNEE.items():
                if token in profile:
                    return role
    return "unknown"


def safe_text(value: Any, max_len: int = 12000) -> str:
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)
    # Redact common token assignment shapes in task prose/metadata, even though
    # callers must not put secrets into Kanban handoffs in the first place.
    text = re.sub(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+", r"\1=<redacted>", text)
    if len(text) > max_len:
        text = text[:max_len] + "…"
    return text


def check_private_boundary_in_text(text: str) -> List[str]:
    lowered = text.lower()
    findings = []
    for token in PRIVATE_TOKENS:
        if token in lowered:
            findings.append(token)
    return sorted(set(findings))


def run_json_command(command: List[str]) -> Dict[str, Any]:
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"command did not return JSON: {' '.join(command)}: {exc}") from exc


def fetch_task(task_id: str, board: Optional[str] = None) -> Dict[str, Any]:
    command = ["hermes", "kanban"]
    if board:
        command.extend(["--board", board])
    command.extend(["show", "--json", task_id])
    return run_json_command(command)


def load_export(path: Path) -> Dict[str, Dict[str, Any]]:
    data = json.loads(path.read_text())
    if isinstance(data, dict) and "tasks" in data and isinstance(data["tasks"], list):
        return {entry["task"]["id"]: entry for entry in data["tasks"] if isinstance(entry, dict) and entry.get("task", {}).get("id")}
    if isinstance(data, list):
        return {entry["task"]["id"]: entry for entry in data if isinstance(entry, dict) and entry.get("task", {}).get("id")}
    if isinstance(data, dict) and data.get("task", {}).get("id"):
        return {data["task"]["id"]: data}
    if isinstance(data, dict):
        return data
    raise ValueError("input JSON must be a script report, a list of kanban-show JSON objects, or one kanban-show JSON object")


def collect_graph(root_task_id: str, board: Optional[str], input_json: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    exported = load_export(input_json) if input_json else {}
    tasks: Dict[str, Dict[str, Any]] = {}
    queue: deque[str] = deque([root_task_id])
    seen = set()
    while queue:
        task_id = queue.popleft()
        if task_id in seen:
            continue
        seen.add(task_id)
        entry = exported.get(task_id) if exported else None
        if entry is None:
            entry = fetch_task(task_id, board=board)
        tasks[task_id] = entry
        children = entry.get("children") or []
        metadata_children = []
        for run in entry.get("runs") or []:
            metadata = run.get("metadata") or {}
            if isinstance(metadata, dict):
                for key in ("created_cards", "remediation_task_ids", "retrigger_task_ids"):
                    vals = metadata.get(key) or []
                    if isinstance(vals, str):
                        vals = [vals]
                    metadata_children.extend(v for v in vals if isinstance(v, str) and v.startswith("t_"))
                chain = metadata.get("created_task_chain")
                if isinstance(chain, dict):
                    metadata_children.extend(v for v in chain.values() if isinstance(v, str) and v.startswith("t_"))
        for child_id in list(children) + metadata_children:
            if child_id not in seen:
                queue.append(child_id)
    return tasks


def parse_lines(body: str, heading_patterns: Iterable[str]) -> List[str]:
    lines = body.splitlines()
    out: List[str] = []
    active = False
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower().rstrip(":")
        if any(re.search(pattern, lower) for pattern in heading_patterns):
            active = True
            continue
        if active:
            if stripped.startswith("##") or (stripped and not stripped.startswith(("-", "*", "[", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")) and stripped.endswith(":")):
                break
            if stripped:
                out.append(stripped.lstrip("- *"))
    return out[:20]


def objective_from_root(root: Dict[str, Any]) -> Dict[str, Any]:
    task = root.get("task") or {}
    body = task.get("body") or ""
    goal_match = re.search(r"(?ims)^goal:\s*(.*?)(?:\n\n|\n(?:context index|scope|acceptance criteria|evidence expectations|blocker)\s*:)", body)
    goal = goal_match.group(1).strip() if goal_match else body.splitlines()[0:1]
    if isinstance(goal, list):
        goal = goal[0] if goal else ""
    acceptance = []
    for line in parse_lines(body, [r"acceptance criteria"]):
        cleaned = re.sub(r"^\d+\.\s*", "", line).strip()
        if cleaned:
            acceptance.append(cleaned)
    scope = parse_lines(body, [r"^scope$", r"^in$", r"^in-scope"])
    out_of_scope = parse_lines(body, [r"out", r"out-of-scope"])
    return {
        "title": task.get("title") or root.get("root_task_id"),
        "goal": safe_text(goal, 4000),
        "scope": scope,
        "out_of_scope": out_of_scope,
        "acceptance_criteria": acceptance,
    }


def final_status(entries: Dict[str, Dict[str, Any]]) -> str:
    statuses = [((entry.get("task") or {}).get("status") or "unknown") for entry in entries.values()]
    if any(s == "blocked" for s in statuses):
        return "blocked"
    if any(s == "running" for s in statuses):
        return "inconclusive"
    if any(s in {"todo", "ready", "triage"} for s in statuses):
        return "inconclusive"
    if all(s == "done" for s in statuses):
        return "succeeded"
    return "inconclusive"


def extract_decisions_and_assumptions(entries: Dict[str, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    decisions = []
    assumptions = []
    did = aid = 1
    for task_id, entry in entries.items():
        for run in entry.get("runs") or []:
            metadata = run.get("metadata") or {}
            if not isinstance(metadata, dict):
                continue
            decision_record = metadata.get("decision_record")
            if isinstance(decision_record, dict):
                for key, value in decision_record.items():
                    decisions.append({"id": f"d{did}", "kind": key, "text": safe_text(value, 1200), "source_task_id": task_id, "evidence_refs": []})
                    did += 1
            for item in metadata.get("decisions") or []:
                if isinstance(item, dict):
                    decisions.append({"id": f"d{did}", "kind": item.get("kind") or "decision", "text": safe_text(item.get("text") or item, 1200), "source_task_id": task_id, "evidence_refs": item.get("evidence_refs") or []})
                    did += 1
            for item in metadata.get("assumptions") or []:
                if isinstance(item, dict):
                    assumptions.append({"id": item.get("id") or f"a{aid}", "text": safe_text(item.get("text") or item, 1200), "source_task_id": task_id, "status": item.get("status") or "unknown"})
                    aid += 1
        for comment in entry.get("comments") or []:
            body = comment.get("body") or ""
            if re.search(r"(?i)decision|approval|approved|rejected|rationale", body):
                decisions.append({"id": f"d{did}", "kind": "approval", "text": safe_text(body, 1800), "source_task_id": task_id, "evidence_refs": []})
                did += 1
    return decisions, assumptions


def extract_evidence(entries: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    evidence = []
    eid = 1
    for task_id, entry in entries.items():
        task = entry.get("task") or {}
        role = task_role(task, entry.get("runs") or [])
        for run in entry.get("runs") or []:
            metadata = run.get("metadata") or {}
            if not isinstance(metadata, dict):
                continue
            for key, value in metadata.items():
                if key in {"private_data_accessed"} and value not in (False, None, "", [], "none", "false"):
                    evidence.append({"id": f"e{eid}", "role": role, "task_id": task_id, "kind": "risk", "label": key, "value": "private-data flag present", "visibility": "internal_non_secret", "verified_by": None, "status": "failed"})
                    eid += 1
                    continue
                if key not in EVIDENCE_KIND_BY_KEY and not any(token in key for token in ("evidence", "artifact", "validation", "commit", "branch", "url", "checkpoint")):
                    continue
                evidence.append({
                    "id": f"e{eid}",
                    "role": role,
                    "task_id": task_id,
                    "kind": EVIDENCE_KIND_BY_KEY.get(key, "artifact"),
                    "label": key,
                    "value": safe_text(value, 2500),
                    "visibility": "internal_non_secret",
                    "verified_by": None,
                    "status": "claimed",
                })
                eid += 1
    return evidence


def build_graph(entries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    nodes = []
    edges = []
    known = set(entries)
    for task_id, entry in entries.items():
        task = entry.get("task") or {}
        role = task_role(task, entry.get("runs") or [])
        nodes.append({
            "task_id": task_id,
            "title": task.get("title"),
            "role": role,
            "assignee": task.get("assignee"),
            "status": task.get("status"),
            "attempt_count": len(entry.get("runs") or []),
        })
        for parent_id in entry.get("parents") or []:
            if parent_id in known:
                edges.append({"from": parent_id, "to": task_id, "kind": "dependency"})
        for child_id in entry.get("children") or []:
            if child_id in known:
                edges.append({"from": task_id, "to": child_id, "kind": "dependency"})
        for run in entry.get("runs") or []:
            metadata = run.get("metadata") or {}
            if not isinstance(metadata, dict):
                continue
            for key, kind in (("remediation_task_ids", "remediation"), ("created_cards", "created_followup"), ("retrigger_task_ids", "created_followup")):
                vals = metadata.get(key) or []
                if isinstance(vals, str):
                    vals = [vals]
                for child_id in vals:
                    if isinstance(child_id, str) and child_id in known:
                        edges.append({"from": task_id, "to": child_id, "kind": kind})
            chain = metadata.get("created_task_chain")
            if isinstance(chain, dict):
                for child_id in chain.values():
                    if isinstance(child_id, str) and child_id in known:
                        edges.append({"from": task_id, "to": child_id, "kind": "created_followup"})
    unique_edges = []
    seen = set()
    for edge in edges:
        key = (edge["from"], edge["to"], edge["kind"])
        if key not in seen:
            unique_edges.append(edge)
            seen.add(key)
    return {"nodes": sorted(nodes, key=lambda n: n["task_id"]), "edges": unique_edges}


def build_timeline(entries: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    timeline = []
    for task_id, entry in entries.items():
        task = entry.get("task") or {}
        role = task_role(task, entry.get("runs") or [])
        for event in entry.get("events") or []:
            kind = event.get("kind") or "event"
            severity = "info"
            if kind in {"blocked", "failed"}:
                severity = "critical"
            timeline.append({
                "time": iso(event.get("created_at")),
                "task_id": task_id,
                "run_id": event.get("run_id"),
                "role": role,
                "kind": kind,
                "summary": safe_text(event.get("payload") or kind, 1000),
                "severity": severity,
                "evidence_refs": [],
            })
        for run in entry.get("runs") or []:
            outcome = run.get("outcome") or run.get("status") or "run"
            severity = "critical" if outcome in {"failed", "blocked", "error"} else "info"
            timeline.append({
                "time": iso(run.get("ended_at") or run.get("started_at")),
                "task_id": task_id,
                "run_id": run.get("id"),
                "role": task_role(task, [run]),
                "kind": f"run_{outcome}",
                "summary": safe_text(run.get("summary") or run.get("error") or outcome, 1400),
                "severity": severity,
                "evidence_refs": [],
            })
    return sorted(timeline, key=lambda e: e.get("time") or "")


def review_outcomes(entries: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    outcomes = []
    for task_id, entry in entries.items():
        task = entry.get("task") or {}
        if task_role(task, entry.get("runs") or []) != "reviewer" and "review" not in str(task.get("title") or "").lower():
            continue
        outcome = "blocked" if task.get("status") == "blocked" else "pass" if task.get("status") == "done" else "inconclusive"
        findings = []
        remediation = []
        retrigger = []
        subjects = entry.get("parents") or []
        for run in entry.get("runs") or []:
            metadata = run.get("metadata") or {}
            if isinstance(metadata, dict):
                outcome = metadata.get("outcome") or outcome
                subjects = metadata.get("review_subject_task_ids") or subjects
                findings.extend([safe_text(f, 1200) for f in (metadata.get("findings") or [])])
                remediation.extend(metadata.get("remediation_task_ids") or [])
                retrigger.extend(metadata.get("retrigger_task_ids") or [])
        outcomes.append({"review_task_id": task_id, "subject_task_ids": subjects, "outcome": outcome, "findings": findings, "remediation_task_ids": remediation, "retrigger_task_ids": retrigger})
    return outcomes


def detect_quality_signals(entries: Dict[str, Dict[str, Any]], graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    signals = []
    children_by_parent: Dict[str, List[str]] = {}
    for edge in graph["edges"]:
        children_by_parent.setdefault(edge["from"], []).append(edge["to"])
    now = datetime.now(timezone.utc).timestamp()
    for task_id, entry in entries.items():
        task = entry.get("task") or {}
        status = task.get("status")
        role = task_role(task, entry.get("runs") or [])
        text_blob = safe_text({"task": task, "runs": entry.get("runs"), "comments": entry.get("comments")}, 30000)
        if status == "blocked" and not children_by_parent.get(task_id) and "unblock" not in text_blob.lower():
            signals.append({"kind": "blocked_without_followup", "severity": "warning", "task_ids": [task_id], "explanation": "Task is blocked, has no child/follow-up task in the traversed graph, and no explicit unblock wording was detected.", "recommended_action": "PM should add unblock criteria or create/link a follow-up task."})
        if status in {"ready", "running"}:
            ts = task.get("started_at") if status == "running" else task.get("created_at")
            age_hours = ((now - float(ts)) / 3600.0) if ts else 0.0
            threshold = 4.0 if status == "ready" else 8.0
            if age_hours > threshold:
                signals.append({"kind": f"stale_{status}", "severity": "warning", "task_ids": [task_id], "explanation": f"Task has been {status} for about {age_hours:.1f} hours (threshold {threshold:.1f}h).", "recommended_action": "Dispatcher/PM should inspect liveness and dependency shape."})
        if "source-update" in text_blob.lower() or "source map" in text_blob.lower():
            required = ["canonical", "worktree", "branch", "affected"]
            missing = [word for word in required if word not in text_blob.lower()]
            if missing:
                signals.append({"kind": "source_map_missing", "severity": "warning", "task_ids": [task_id], "explanation": f"Source-update-like task is missing Source Map tokens: {', '.join(missing)}.", "recommended_action": "PM should add a complete Source Map before implementation/review."})
        if role in ROLE_REQUIRED_EVIDENCE and status == "done":
            metadata_keys = set()
            for run in entry.get("runs") or []:
                metadata = run.get("metadata") or {}
                if isinstance(metadata, dict):
                    metadata_keys.update(metadata.keys())
            required_keys = ROLE_REQUIRED_EVIDENCE[role]
            missing_keys = [key for key in required_keys if key not in metadata_keys]
            if missing_keys:
                signals.append({"kind": "missing_evidence", "severity": "warning", "task_ids": [task_id], "explanation": f"Completed {role} task lacks expected evidence metadata keys: {', '.join(missing_keys)}.", "recommended_action": "Reviewer/PM should request a richer handoff or attach evidence."})
        # Naming forbidden objects in boundary guidance is expected. Flag only
        # assignment-like secret leakage patterns, not no-secret policy prose.
        if re.search(r"(?i)(api[_-]?key|oauth[_-]?token|ssh[_-]?key|secret|password)\s*[:=]\s*[^\s,;]+", text_blob):
            signals.append({"kind": "private_boundary_risk", "severity": "critical", "task_ids": [task_id], "explanation": "Potential assignment-like secret value detected in task text/metadata.", "recommended_action": "Inspect report inputs and remove/replace private state references before sharing."})
        for run in entry.get("runs") or []:
            if re.search(r"forced skill|skill_context_failure|mandatory skill", safe_text(run, 4000), flags=re.I):
                signals.append({"kind": "forced_skill_crash", "severity": "critical", "task_ids": [task_id], "explanation": "Run text references a forced/mandatory skill failure.", "recommended_action": "PM should route profile/skill installation remediation before redispatch."})
        for event in entry.get("events") or []:
            if re.search(r"hallucinated.*created.*card|phantom.*card", safe_text(event, 2000), flags=re.I):
                signals.append({"kind": "hallucinated_created_card", "severity": "critical", "task_ids": [task_id], "explanation": "Task event stream reports a hallucinated/phantom created card claim.", "recommended_action": "Worker/PM should correct completion metadata and create/link only verified Kanban task ids."})
    for edge in graph["edges"]:
        parent_task = entries.get(edge["from"], {}).get("task", {})
        child_task = entries.get(edge["to"], {}).get("task", {})
        if parent_task.get("status") == "blocked" and re.search(r"approval|decision|gate|unblock", str(child_task.get("title") or ""), flags=re.I):
            signals.append({"kind": "child_under_blocked_parent_deadlock", "severity": "critical", "task_ids": [edge["from"], edge["to"]], "explanation": "An approval/decision/unblocker-looking child depends on a blocked parent.", "recommended_action": "Create the decision gate as an unparented sibling or parent of future execution work."})
    for review in review_outcomes(entries):
        if str(review.get("outcome")).lower() in {"fail", "failed", "blocked"} and not review.get("remediation_task_ids"):
            signals.append({"kind": "reviewer_without_remediation", "severity": "warning", "task_ids": [review["review_task_id"]], "explanation": "Reviewer fail/block outcome has no remediation_task_ids in normalized metadata.", "recommended_action": "PM should create/link remediation or explicitly document why none is needed."})
    return signals


def unresolved_risks(signals: List[Dict[str, Any]], entries: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    risks = []
    for signal in signals:
        if signal["severity"] in {"warning", "critical"}:
            risks.append({"kind": signal["kind"], "text": signal["explanation"], "owner": "pm", "blocking": signal["severity"] == "critical"})
    for task_id, entry in entries.items():
        task = entry.get("task") or {}
        if task.get("status") == "blocked":
            risks.append({"kind": "authority", "text": f"Blocked task {task_id}: {task.get('title')}", "owner": task_role(task, entry.get("runs") or []), "blocking": True})
    return risks


def build_report(root_task_id: str, entries: Dict[str, Dict[str, Any]], output_dir: Path) -> Dict[str, Any]:
    if root_task_id not in entries:
        raise ValueError(f"root task {root_task_id} not found in collected graph")
    root = entries[root_task_id]
    graph = build_graph(entries)
    evidence = extract_evidence(entries)
    decisions, assumptions = extract_decisions_and_assumptions(entries)
    signals = detect_quality_signals(entries, graph)
    status = final_status(entries)
    root_task = root.get("task") or {}
    done_claim = "Interim report: task graph is not fully closed."
    if status == "succeeded":
        done_claim = f"Task graph rooted at {root_task_id} is complete; evidence and risks are summarized in this report."
    elif status == "blocked":
        done_claim = f"Task graph rooted at {root_task_id} is blocked; see unresolved risks and quality signals."
    elif status == "succeeded_with_risks":
        done_claim = f"Task graph rooted at {root_task_id} is complete with unresolved risks."
    report = {
        "report_version": REPORT_VERSION,
        "root_task_id": root_task_id,
        "generated_at": now_iso(),
        "status": status,
        "done_claim": done_claim,
        "objective": objective_from_root(root),
        "assumptions": assumptions,
        "decisions": decisions,
        "task_graph": graph,
        "timeline": build_timeline(entries),
        "evidence": evidence,
        "review_outcomes": review_outcomes(entries),
        "quality_signals": signals,
        "unresolved_risks": unresolved_risks(signals, entries),
        "delivery": {
            "channel": "artifact_path",
            "artifact_refs": [],
            "regeneration_command_or_endpoint": f"python scripts/software_factory_evidence_report.py {root_task_id} --out-dir {output_dir}",
        },
        "audit_appendix": {
            "public_private_boundary": "Generated from public Kanban CLI/API JSON or caller-provided public-safe JSON export only; raw DBs, .env/auth files, sessions, memories, logs, local profile state, private notes, OAuth/API/SSH credentials are out of scope.",
            "task_count": len(entries),
            "task_ids": sorted(entries),
        },
    }
    return report


def render_html(report: Dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(safe_text(value, 6000))

    def table(headers: List[str], rows: List[List[Any]]) -> str:
        head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
        body = "".join("<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in row) + "</tr>" for row in rows)
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    graph = report["task_graph"]
    html_parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        f"<title>Software Factory Evidence Report {html.escape(report['root_task_id'])}</title>",
        "<style>body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:2rem;line-height:1.4}table{border-collapse:collapse;width:100%;margin:1rem 0}td,th{border:1px solid #ddd;padding:.45rem;vertical-align:top}th{background:#f5f5f5}code,pre{background:#f7f7f7;padding:.2rem}.critical{color:#b00020;font-weight:700}.warning{color:#8a5a00;font-weight:700}.section{margin-top:2rem}</style>",
        "</head><body>",
        f"<h1>Software Factory Evidence Report: {html.escape(report['root_task_id'])}</h1>",
        f"<p><strong>Status:</strong> {html.escape(report['status'])}<br><strong>Generated:</strong> {html.escape(report['generated_at'])}<br><strong>Done claim:</strong> {esc(report['done_claim'])}</p>",
        "<div class='section'><h2>Objective and scope</h2>",
        f"<p><strong>Title:</strong> {esc(report['objective'].get('title'))}</p><p><strong>Goal:</strong> {esc(report['objective'].get('goal'))}</p>",
        f"<p><strong>Acceptance criteria:</strong></p><ul>{''.join('<li>'+esc(x)+'</li>' for x in report['objective'].get('acceptance_criteria', []))}</ul></div>",
        "<div class='section'><h2>Assumptions and PM decisions</h2>",
        table(["id", "kind/status", "source", "text"], [[d.get("id"), d.get("kind") or d.get("status"), d.get("source_task_id"), d.get("text")] for d in report["decisions"] + report["assumptions"]]),
        "</div><div class='section'><h2>Task graph</h2>",
        table(["task", "role", "assignee", "status", "attempts", "title"], [[n.get("task_id"), n.get("role"), n.get("assignee"), n.get("status"), n.get("attempt_count"), n.get("title")] for n in graph["nodes"]]),
        "<h3>Edges</h3>",
        table(["from", "to", "kind"], [[e.get("from"), e.get("to"), e.get("kind")] for e in graph["edges"]]),
        "</div><div class='section'><h2>Evidence by role</h2>",
        table(["id", "role", "task", "kind", "label", "status", "value"], [[e.get("id"), e.get("role"), e.get("task_id"), e.get("kind"), e.get("label"), e.get("status"), e.get("value")] for e in report["evidence"]]),
        "</div><div class='section'><h2>Review outcomes and remediation loops</h2>",
        table(["review task", "outcome", "subjects", "remediation", "retrigger", "findings"], [[r.get("review_task_id"), r.get("outcome"), r.get("subject_task_ids"), r.get("remediation_task_ids"), r.get("retrigger_task_ids"), r.get("findings")] for r in report["review_outcomes"]]),
        "</div><div class='section'><h2>Launch/deploy proof</h2><p>No runtime launch/deploy is assumed by this generator. See evidence rows for URLs, publication refs, install proof, checkpoints, or explicit not-in-scope handoff notes.</p></div>",
        "<div class='section'><h2>Deadlock/quality signals</h2>",
        table(["severity", "kind", "tasks", "explanation", "recommended action"], [[s.get("severity"), s.get("kind"), s.get("task_ids"), s.get("explanation"), s.get("recommended_action")] for s in report["quality_signals"]]),
        "</div><div class='section'><h2>Unresolved risks</h2>",
        table(["kind", "owner", "blocking", "text"], [[r.get("kind"), r.get("owner"), r.get("blocking"), r.get("text")] for r in report["unresolved_risks"]]),
        "</div><div class='section'><h2>Audit appendix / timeline</h2>",
        f"<p>{esc(report['audit_appendix']['public_private_boundary'])}</p>",
        table(["time", "task", "run", "role", "kind", "severity", "summary"], [[t.get("time"), t.get("task_id"), t.get("run_id"), t.get("role"), t.get("kind"), t.get("severity"), t.get("summary")] for t in report["timeline"]]),
        "</div></body></html>",
    ]
    return "\n".join(html_parts)


def write_outputs(report: Dict[str, Any], output_dir: Path, root_task_id: str) -> Tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{root_task_id}-software-factory-evidence-report"
    json_path = output_dir / f"{stem}.json"
    html_path = output_dir / f"{stem}.html"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True))
    html_path.write_text(render_html(report))
    report["delivery"]["artifact_refs"] = [str(html_path), str(json_path)]
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True))
    return html_path, json_path


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Software Factory PM evidence HTML + JSON report from public Kanban task JSON.")
    parser.add_argument("root_task_id", help="Root Kanban task id to traverse, for example t_497fcb77")
    parser.add_argument("--board", default=os.environ.get("HERMES_KANBAN_BOARD"), help="Kanban board slug to pass to `hermes kanban --board`; defaults to HERMES_KANBAN_BOARD/current board")
    parser.add_argument("--out-dir", default="./sf-evidence-reports", help="Directory for generated HTML and JSON artifacts")
    parser.add_argument("--input-json", type=Path, help="Optional public-safe export of kanban-show JSON objects; avoids live Kanban CLI calls")
    parser.add_argument("--max-tasks", type=int, default=200, help="Safety cap after graph collection")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.out_dir).expanduser().resolve()
    entries = collect_graph(args.root_task_id, board=args.board, input_json=args.input_json)
    if len(entries) > args.max_tasks:
        raise RuntimeError(f"collected {len(entries)} tasks, above --max-tasks={args.max_tasks}")
    report = build_report(args.root_task_id, entries, output_dir)
    html_path, json_path = write_outputs(report, output_dir, args.root_task_id)
    print(json.dumps({"status": "ok", "root_task_id": args.root_task_id, "task_count": len(entries), "html": str(html_path), "json": str(json_path), "quality_signal_count": len(report["quality_signals"]), "report_status": report["status"]}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
