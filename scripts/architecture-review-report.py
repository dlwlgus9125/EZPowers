#!/usr/bin/env python3
"""Render a validated, offline EZPowers architecture review report."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any
import uuid
import webbrowser


SCHEMA_VERSION = 2
MAX_INPUT_BYTES = 1024 * 1024
MAX_CANDIDATES = 8
MAX_LIST_ITEMS = 20
MAX_NODES = 24
MAX_EDGES = 48
MAX_PROSE = 8000
MAX_LABEL = 200
MAX_PATH = 512
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
STRENGTHS = {"strong", "worth_exploring", "speculative"}
NODE_KINDS = {"caller", "module", "adapter", "dependency", "data", "external"}
NODE_EMPHASES = {"normal", "shallow", "deep", "faded"}
EDGE_KINDS = {"call", "dependency", "leak", "seam"}
EVIDENCE_ROLES = {"product", "test", "context", "decision"}
SCOPE_BASES = {"user_named", "git_hotspot", "widened"}
ADR_STATUSES = {"none", "aligned", "conflicts", "revisit"}


class ReportError(ValueError):
    """Raised when report input or output violates the renderer contract."""


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReportError(f"{label} must be an object")
    return value


def _require_keys(
    value: dict[str, Any],
    *,
    required: set[str],
    optional: set[str] = frozenset(),
    label: str,
) -> None:
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required - optional)
    if missing:
        raise ReportError(f"{label} is missing fields: {', '.join(missing)}")
    if unknown:
        raise ReportError(f"{label} has unknown fields: {', '.join(unknown)}")


def _text(value: Any, label: str, maximum: int = MAX_PROSE) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReportError(f"{label} must be a non-empty string")
    result = value.strip()
    if len(result) > maximum:
        raise ReportError(f"{label} exceeds {maximum} characters")
    return result


def _identifier(value: Any, label: str) -> str:
    result = _text(value, label, 64)
    if ID_RE.fullmatch(result) is None:
        raise ReportError(f"{label} must be lower-case hyphen form")
    return result


def _bounded_list(
    value: Any,
    label: str,
    *,
    minimum: int = 1,
    maximum: int = MAX_LIST_ITEMS,
) -> list[Any]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ReportError(f"{label} must contain {minimum}-{maximum} items")
    return value


def _within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _repo_path(
    value: Any,
    label: str,
    project_root: Path,
    *,
    file_only: bool,
) -> str:
    raw = _text(value, label, MAX_PATH).replace("\\", "/")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ReportError(
            f"{label} contains an unsafe path; expected a repository-relative path"
        )
    resolved = (project_root / Path(*pure.parts)).resolve()
    if not _within(resolved, project_root):
        raise ReportError(f"{label} escapes the project root")
    if file_only and not resolved.is_file():
        raise ReportError(f"{label} must identify an existing file: {raw}")
    if not file_only and not resolved.exists():
        raise ReportError(f"{label} must identify an existing path: {raw}")
    return pure.as_posix()


def _validate_source_line(
    project_root: Path,
    relative_path: str,
    line: int,
    label: str,
) -> None:
    source = project_root / Path(*PurePosixPath(relative_path).parts)
    try:
        line_count = len(source.read_text(encoding="utf-8-sig").splitlines())
    except (OSError, UnicodeError) as exc:
        raise ReportError(f"{label} must identify a readable UTF-8 text file") from exc
    if line > line_count:
        raise ReportError(
            f"{label}.line exceeds the file length ({line_count} lines)"
        )


def _validate_timestamp(value: Any) -> str:
    result = _text(value, "generated_at", 64)
    try:
        parsed = dt.datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReportError("generated_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ReportError("generated_at must include a timezone")
    return result


def _validate_graph(value: Any, label: str) -> dict[str, Any]:
    graph = _require_object(value, label)
    _require_keys(graph, required={"nodes", "edges"}, label=label)
    raw_nodes = _bounded_list(graph["nodes"], f"{label}.nodes", maximum=MAX_NODES)
    raw_edges = _bounded_list(
        graph["edges"],
        f"{label}.edges",
        minimum=0,
        maximum=MAX_EDGES,
    )
    nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    for index, raw_node in enumerate(raw_nodes):
        node_label = f"{label}.nodes[{index}]"
        node = _require_object(raw_node, node_label)
        _require_keys(
            node,
            required={"id", "label", "layer", "kind"},
            optional={"emphasis"},
            label=node_label,
        )
        node_id = _identifier(node["id"], f"{node_label}.id")
        if node_id in node_ids:
            raise ReportError(f"{label} has duplicate node id: {node_id}")
        node_ids.add(node_id)
        layer = node["layer"]
        if isinstance(layer, bool) or not isinstance(layer, int) or not 0 <= layer <= 7:
            raise ReportError(f"{node_label}.layer must be an integer from 0 through 7")
        kind = _text(node["kind"], f"{node_label}.kind", 32)
        if kind not in NODE_KINDS:
            raise ReportError(f"{node_label}.kind is invalid")
        emphasis = _text(
            node.get("emphasis", "normal"),
            f"{node_label}.emphasis",
            32,
        )
        if emphasis not in NODE_EMPHASES:
            raise ReportError(f"{node_label}.emphasis is invalid")
        nodes.append(
            {
                "id": node_id,
                "label": _text(node["label"], f"{node_label}.label", MAX_LABEL),
                "layer": layer,
                "kind": kind,
                "emphasis": emphasis,
            }
        )
    edges: list[dict[str, str]] = []
    for index, raw_edge in enumerate(raw_edges):
        edge_label = f"{label}.edges[{index}]"
        edge = _require_object(raw_edge, edge_label)
        _require_keys(
            edge,
            required={"from", "to"},
            optional={"label", "kind"},
            label=edge_label,
        )
        source = _identifier(edge["from"], f"{edge_label}.from")
        target = _identifier(edge["to"], f"{edge_label}.to")
        if source not in node_ids or target not in node_ids:
            raise ReportError(f"{edge_label} has a dangling endpoint")
        kind = _text(edge.get("kind", "call"), f"{edge_label}.kind", 32)
        if kind not in EDGE_KINDS:
            raise ReportError(f"{edge_label}.kind is invalid")
        edges.append(
            {
                "from": source,
                "to": target,
                "kind": kind,
                "label": (
                    _text(edge["label"], f"{edge_label}.label", MAX_LABEL)
                    if "label" in edge
                    else ""
                ),
            }
        )
    return {"nodes": nodes, "edges": edges}


def validate_report(value: Any, project_root: Path) -> dict[str, Any]:
    report = _require_object(value, "report")
    _require_keys(
        report,
        required={
            "schema_version",
            "repository",
            "scope",
            "scope_basis",
            "scope_rationale",
            "generated_at",
            "top_recommendation",
            "candidates",
        },
        optional={"language"},
        label="report",
    )
    if report["schema_version"] != SCHEMA_VERSION:
        raise ReportError(f"schema_version must be {SCHEMA_VERSION}")
    language = report.get("language", "en")
    if not isinstance(language, str) or LANGUAGE_RE.fullmatch(language) is None:
        raise ReportError("language must be a BCP-47-style language tag")
    scope_basis = _text(report["scope_basis"], "scope_basis", 32)
    if scope_basis not in SCOPE_BASES:
        raise ReportError("scope_basis is invalid")
    repository = _require_object(report["repository"], "repository")
    _require_keys(
        repository,
        required={"name", "revision", "dirty"},
        label="repository",
    )
    if not isinstance(repository["dirty"], bool):
        raise ReportError("repository.dirty must be a boolean")
    clean_repository = {
        "name": _text(repository["name"], "repository.name", MAX_LABEL),
        "revision": _text(repository["revision"], "repository.revision", MAX_LABEL),
        "dirty": repository["dirty"],
    }
    raw_candidates = _bounded_list(
        report["candidates"],
        "candidates",
        maximum=MAX_CANDIDATES,
    )
    candidates: list[dict[str, Any]] = []
    candidate_ids: set[str] = set()
    for index, raw_candidate in enumerate(raw_candidates):
        label = f"candidates[{index}]"
        candidate = _require_object(raw_candidate, label)
        _require_keys(
            candidate,
            required={
                "id",
                "title",
                "strength",
                "files",
                "evidence",
                "problem",
                "solution",
                "benefits",
                "test_effect",
                "compatibility",
                "migration",
                "adr",
                "before",
                "after",
            },
            label=label,
        )
        candidate_id = _identifier(candidate["id"], f"{label}.id")
        if candidate_id in candidate_ids:
            raise ReportError(f"duplicate candidate id: {candidate_id}")
        candidate_ids.add(candidate_id)
        strength = _text(candidate["strength"], f"{label}.strength", 32)
        if strength not in STRENGTHS:
            raise ReportError(f"{label}.strength is invalid")
        raw_files = _bounded_list(candidate["files"], f"{label}.files")
        files = [
            _repo_path(item, f"{label}.files[{item_index}]", project_root, file_only=True)
            for item_index, item in enumerate(raw_files)
        ]
        if len(files) != len(set(files)):
            raise ReportError(f"{label}.files contains duplicates")
        raw_evidence = _bounded_list(candidate["evidence"], f"{label}.evidence")
        evidence: list[dict[str, Any]] = []
        evidence_locations: set[tuple[str, int]] = set()
        for evidence_index, raw_item in enumerate(raw_evidence):
            item_label = f"{label}.evidence[{evidence_index}]"
            item = _require_object(raw_item, item_label)
            _require_keys(
                item,
                required={"path", "line", "role", "finding"},
                label=item_label,
            )
            line = item["line"]
            if isinstance(line, bool) or not isinstance(line, int) or line < 1:
                raise ReportError(f"{item_label}.line must be a positive integer")
            path = _repo_path(
                item["path"],
                f"{item_label}.path",
                project_root,
                file_only=True,
            )
            _validate_source_line(project_root, path, line, item_label)
            location = (path, line)
            if location in evidence_locations:
                raise ReportError(f"{label}.evidence contains duplicate path and line")
            evidence_locations.add(location)
            role = _text(item["role"], f"{item_label}.role", 32)
            if role not in EVIDENCE_ROLES:
                raise ReportError(f"{item_label}.role is invalid")
            evidence.append(
                {
                    "path": path,
                    "line": line,
                    "role": role,
                    "finding": _text(item["finding"], f"{item_label}.finding"),
                }
            )
        covered_files = {
            item["path"]
            for item in evidence
            if item["role"] in {"product", "test"}
        }
        if set(files) != covered_files:
            raise ReportError(
                f"{label}.evidence with product/test roles must cover every "
                "candidate file and no other files"
            )
        raw_adr = _require_object(candidate["adr"], f"{label}.adr")
        _require_keys(
            raw_adr,
            required={"status", "references", "finding"},
            label=f"{label}.adr",
        )
        adr_status = _text(raw_adr["status"], f"{label}.adr.status", 32)
        if adr_status not in ADR_STATUSES:
            raise ReportError(f"{label}.adr.status is invalid")
        raw_adr_references = _bounded_list(
            raw_adr["references"],
            f"{label}.adr.references",
            minimum=0,
        )
        adr_references = [
            _repo_path(
                item,
                f"{label}.adr.references[{reference_index}]",
                project_root,
                file_only=True,
            )
            for reference_index, item in enumerate(raw_adr_references)
        ]
        if len(adr_references) != len(set(adr_references)):
            raise ReportError(f"{label}.adr.references contains duplicates")
        if adr_status == "none" and adr_references:
            raise ReportError(f"{label}.adr.references must be empty when status is none")
        if adr_status != "none" and not adr_references:
            raise ReportError(
                f"{label}.adr.references requires at least one file for {adr_status}"
            )
        decision_evidence = {
            item["path"] for item in evidence if item["role"] == "decision"
        }
        if not set(adr_references).issubset(decision_evidence):
            raise ReportError(
                f"{label}.adr.references must have line-specific decision evidence"
            )
        raw_benefits = _bounded_list(candidate["benefits"], f"{label}.benefits")
        candidates.append(
            {
                "id": candidate_id,
                "title": _text(candidate["title"], f"{label}.title", MAX_LABEL),
                "strength": strength,
                "files": files,
                "evidence": evidence,
                "problem": _text(candidate["problem"], f"{label}.problem"),
                "solution": _text(candidate["solution"], f"{label}.solution"),
                "benefits": [
                    _text(item, f"{label}.benefits[{benefit_index}]")
                    for benefit_index, item in enumerate(raw_benefits)
                ],
                "test_effect": _text(candidate["test_effect"], f"{label}.test_effect"),
                "compatibility": _text(
                    candidate["compatibility"],
                    f"{label}.compatibility",
                ),
                "migration": _text(candidate["migration"], f"{label}.migration"),
                "adr": {
                    "status": adr_status,
                    "references": adr_references,
                    "finding": _text(raw_adr["finding"], f"{label}.adr.finding"),
                },
                "before": _validate_graph(candidate["before"], f"{label}.before"),
                "after": _validate_graph(candidate["after"], f"{label}.after"),
            }
        )
    top = _require_object(report["top_recommendation"], "top_recommendation")
    _require_keys(
        top,
        required={"candidate_id", "rationale"},
        label="top_recommendation",
    )
    top_id = _identifier(top["candidate_id"], "top_recommendation.candidate_id")
    if top_id not in candidate_ids:
        raise ReportError("top_recommendation.candidate_id does not identify a candidate")
    return {
        "schema_version": SCHEMA_VERSION,
        "language": language,
        "repository": clean_repository,
        "scope": _text(report["scope"], "scope"),
        "scope_basis": scope_basis,
        "scope_rationale": _text(report["scope_rationale"], "scope_rationale"),
        "generated_at": _validate_timestamp(report["generated_at"]),
        "top_recommendation": {
            "candidate_id": top_id,
            "rationale": _text(top["rationale"], "top_recommendation.rationale"),
        },
        "candidates": candidates,
    }


def _graph_svg(graph: dict[str, Any], prefix: str, title: str) -> str:
    layers: dict[int, list[dict[str, Any]]] = {}
    for node in graph["nodes"]:
        layers.setdefault(node["layer"], []).append(node)
    ordered_layers = sorted(layers)
    width = 680
    top = 54
    row_height = 112
    node_height = 54
    height = top + len(ordered_layers) * row_height + 28
    positions: dict[str, tuple[float, float]] = {}
    node_parts: list[str] = []
    for row_index, layer in enumerate(ordered_layers):
        nodes = layers[layer]
        gap = 18
        usable = width - 40 - gap * max(0, len(nodes) - 1)
        node_width = min(190.0, usable / len(nodes))
        total = node_width * len(nodes) + gap * max(0, len(nodes) - 1)
        start = (width - total) / 2
        y = top + row_index * row_height
        for column, node in enumerate(nodes):
            x = start + column * (node_width + gap)
            positions[node["id"]] = (x + node_width / 2, y + node_height / 2)
            visible = node["label"] if len(node["label"]) <= 42 else node["label"][:39] + "..."
            node_parts.append(
                f'<g class="graph-node kind-{node["kind"]} '
                f'emphasis-{node["emphasis"]}">'
                f"<title>{html.escape(node['label'])}</title>"
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{node_width:.1f}" '
                f'height="{node_height}" rx="12"></rect>'
                f'<text x="{x + node_width / 2:.1f}" y="{y + 32:.1f}" '
                f'text-anchor="middle">{html.escape(visible)}</text></g>'
            )
    marker_ids = {
        kind: f"arrow-{prefix}-{kind}"
        for kind in sorted(EDGE_KINDS)
    }
    marker_parts = [
        f'<marker class="marker-{kind}" id="{marker_id}" viewBox="0 0 10 10" '
        'refX="9" refY="5" markerWidth="6" markerHeight="6" '
        'orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z"></path></marker>'
        for kind, marker_id in marker_ids.items()
    ]
    edge_parts: list[str] = []
    for edge in graph["edges"]:
        source_x, source_y = positions[edge["from"]]
        target_x, target_y = positions[edge["to"]]
        marker_id = marker_ids[edge["kind"]]
        edge_parts.append(
            f'<line class="edge-{edge["kind"]}" '
            f'x1="{source_x:.1f}" y1="{source_y + node_height / 2:.1f}" '
            f'x2="{target_x:.1f}" y2="{target_y - node_height / 2:.1f}" '
            f'marker-end="url(#{marker_id})"></line>'
        )
        if edge["label"]:
            edge_parts.append(
                f'<text class="edge-label" x="{(source_x + target_x) / 2:.1f}" '
                f'y="{(source_y + target_y) / 2 - 5:.1f}" text-anchor="middle">'
                f"{html.escape(edge['label'])}</text>"
            )
    return (
        f'<svg class="architecture-graph" viewBox="0 0 {width} {height}" '
        f'role="img" aria-labelledby="{prefix}-title {prefix}-desc">'
        f'<title id="{prefix}-title">{html.escape(title)}</title>'
        f'<desc id="{prefix}-desc">Layered module, seam, and dependency diagram.</desc>'
        f"<defs>{''.join(marker_parts)}</defs>"
        + "".join(edge_parts)
        + "".join(node_parts)
        + "</svg>"
    )


def render_html(report: dict[str, Any]) -> str:
    repository = report["repository"]
    top_recommendation = report["top_recommendation"]
    top_candidate = next(
        candidate
        for candidate in report["candidates"]
        if candidate["id"] == top_recommendation["candidate_id"]
    )
    candidate_parts: list[str] = []
    for index, candidate in enumerate(report["candidates"], 1):
        top = candidate["id"] == top_recommendation["candidate_id"]
        evidence_items = "".join(
            "<li><code>"
            + html.escape(item["path"])
            + f":{item['line']}"
            + "</code><span class=\"evidence-role\">"
            + html.escape(item["role"])
            + "</span><span>"
            + html.escape(item["finding"])
            + "</span></li>"
            for item in candidate["evidence"]
        )
        file_chips = "".join(
            f"<code class=\"file-chip\">{html.escape(path)}</code>"
            for path in candidate["files"]
        )
        benefits = "".join(
            f"<li>{html.escape(benefit)}</li>" for benefit in candidate["benefits"]
        )
        adr_references = "".join(
            f'<code class="file-chip">{html.escape(path)}</code>'
            for path in candidate["adr"]["references"]
        )
        strength = candidate["strength"].replace("_", " ")
        candidate_parts.append(
            f'<article class="candidate{" top" if top else ""}" id="{candidate["id"]}">'
            '<header class="candidate-header"><div>'
            f'<span class="candidate-index">Candidate {index:02d}</span>'
            f"<h2>{html.escape(candidate['title'])}</h2></div>"
            f'<span class="strength strength-{candidate["strength"]}">'
            f"{html.escape(strength)}</span></header>"
            + ('<p class="top-label">Top recommendation</p>' if top else "")
            + f'<div class="file-list">{file_chips}</div>'
            + '<div class="candidate-copy"><section><h3>Problem</h3>'
            + f"<p>{html.escape(candidate['problem'])}</p></section>"
            + "<section><h3>Deepening</h3>"
            + f"<p>{html.escape(candidate['solution'])}</p></section></div>"
            + '<section><h3>Repository evidence</h3>'
            + f'<ul class="evidence-list">{evidence_items}</ul></section>'
            + '<div class="diagrams"><section><h3>Before</h3>'
            + _graph_svg(candidate["before"], f"{candidate['id']}-before", "Before")
            + '</section><section><h3>After</h3>'
            + _graph_svg(candidate["after"], f"{candidate['id']}-after", "After")
            + "</section></div>"
            + '<div class="candidate-copy"><section><h3>Benefits</h3>'
            + f"<ul>{benefits}</ul></section>"
            + "<section><h3>Test effect</h3>"
            + f"<p>{html.escape(candidate['test_effect'])}</p></section></div>"
            + '<div class="candidate-copy"><section><h3>Compatibility</h3>'
            + f"<p>{html.escape(candidate['compatibility'])}</p></section>"
            + "<section><h3>Migration</h3>"
            + f"<p>{html.escape(candidate['migration'])}</p></section></div>"
            + f'<section class="adr-callout adr-{candidate["adr"]["status"]}">'
            + "<h3>ADR context</h3>"
            + f'<p><strong>{html.escape(candidate["adr"]["status"])}</strong> '
            + html.escape(candidate["adr"]["finding"])
            + "</p>"
            + (f'<div class="file-list">{adr_references}</div>' if adr_references else "")
            + "</section>"
            + "</article>"
        )
    dirty = "dirty working tree" if repository["dirty"] else "clean working tree"
    scope_basis = report["scope_basis"].replace("_", " ")
    return f"""<!doctype html>
<html lang="{html.escape(report['language'])}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; font-src 'none'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">
  <title>Architecture review — {html.escape(repository['name'])}</title>
  <style>
    :root {{ color-scheme: light dark; --paper:#fbfaf5; --card:#fff; --ink:#17202a; --muted:#667085; --line:#d8d4c7; --blue:#2756d7; --mint:#087f5b; --amber:#a15c00; --coral:#b42318; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--paper); color:var(--ink); font:16px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif; }}
    main {{ width:min(1180px,calc(100% - 32px)); margin:0 auto; padding:56px 0 80px; }}
    h1,h2,h3,p {{ margin-top:0; }}
    h1 {{ max-width:900px; font-size:clamp(2.25rem,6vw,4.8rem); line-height:1.02; letter-spacing:-.045em; }}
    h2 {{ font-size:clamp(1.55rem,3vw,2.35rem); line-height:1.12; }}
    h3 {{ font-size:.78rem; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); }}
    .eyebrow,.candidate-index {{ color:var(--blue); font-weight:750; letter-spacing:.12em; text-transform:uppercase; font-size:.75rem; }}
    .lede {{ max-width:760px; font-size:1.15rem; color:var(--muted); }}
    .meta {{ display:flex; flex-wrap:wrap; gap:8px; margin:24px 0 44px; }}
    .meta span,.file-chip {{ border:1px solid var(--line); border-radius:999px; padding:6px 11px; background:var(--card); }}
    .top-recommendation {{ margin:30px 0 44px; padding:24px 28px; border-left:5px solid var(--blue); background:var(--card); border-radius:0 18px 18px 0; }}
    .top-recommendation h2 {{ margin-bottom:8px; }}
    .top-recommendation a {{ color:var(--blue); font-weight:750; }}
    .candidate {{ margin:28px 0; padding:clamp(22px,4vw,42px); background:var(--card); border:1px solid var(--line); border-radius:24px; box-shadow:0 14px 34px rgba(25,30,45,.06); }}
    .candidate.top {{ border:2px solid var(--blue); }}
    .candidate-header {{ display:flex; align-items:flex-start; justify-content:space-between; gap:18px; }}
    .strength {{ white-space:nowrap; border-radius:999px; padding:7px 12px; font-size:.78rem; font-weight:750; text-transform:capitalize; }}
    .strength-strong {{ background:#d7f5e8; color:#086044; }}
    .strength-worth_exploring {{ background:#fff0cc; color:#744400; }}
    .strength-speculative {{ background:#f2f4f7; color:#475467; }}
    .top-label {{ color:var(--blue); font-weight:750; }}
    .file-list {{ display:flex; flex-wrap:wrap; gap:7px; margin:18px 0 28px; }}
    .file-chip {{ font-size:.76rem; overflow-wrap:anywhere; }}
    .candidate-copy,.diagrams {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:24px; margin:28px 0; }}
    .candidate-copy section,.diagrams section {{ min-width:0; }}
    .evidence-list {{ list-style:none; padding:0; display:grid; gap:9px; }}
    .evidence-list li {{ display:grid; grid-template-columns:minmax(150px,.38fr) auto 1fr; gap:12px; border-top:1px solid var(--line); padding-top:9px; }}
    .evidence-list code {{ overflow-wrap:anywhere; color:var(--blue); }}
    .evidence-role {{ align-self:start; border:1px solid var(--line); border-radius:999px; padding:1px 7px; color:var(--muted); font-size:.7rem; text-transform:uppercase; }}
    .architecture-graph {{ width:100%; height:auto; border:1px solid var(--line); border-radius:16px; background:var(--paper); }}
    .architecture-graph line {{ stroke:#7b8494; stroke-width:2; }}
    .architecture-graph marker path {{ fill:#7b8494; }}
    .architecture-graph line.edge-leak {{ stroke:var(--coral); stroke-width:3; }}
    .architecture-graph .marker-leak path {{ fill:var(--coral); }}
    .architecture-graph line.edge-seam {{ stroke:var(--mint); stroke-dasharray:8 6; }}
    .architecture-graph .marker-seam path {{ fill:var(--mint); }}
    .architecture-graph line.edge-dependency {{ stroke:var(--amber); }}
    .architecture-graph .marker-dependency path {{ fill:var(--amber); }}
    .architecture-graph rect {{ fill:#eef2ff; stroke:#7086c7; stroke-width:1.5; }}
    .architecture-graph .kind-adapter rect {{ fill:#dff7ed; stroke:#45a783; }}
    .architecture-graph .kind-external rect,.architecture-graph .kind-dependency rect {{ fill:#fff0d6; stroke:#c88a33; }}
    .architecture-graph .emphasis-shallow rect {{ stroke-dasharray:7 5; }}
    .architecture-graph .emphasis-deep rect {{ stroke:var(--blue); stroke-width:4; }}
    .architecture-graph .emphasis-faded {{ opacity:.45; }}
    .architecture-graph text {{ fill:var(--ink); font-size:13px; font-weight:650; }}
    .architecture-graph .edge-label {{ font-size:10px; font-weight:500; fill:var(--muted); paint-order:stroke; stroke:var(--paper); stroke-width:4px; }}
    .adr-callout {{ margin-top:28px; padding:18px 20px; border:1px solid var(--line); border-radius:16px; }}
    .adr-conflicts,.adr-revisit {{ border-color:var(--amber); background:color-mix(in srgb,var(--amber) 8%,transparent); }}
    footer {{ margin-top:50px; padding-top:20px; border-top:1px solid var(--line); color:var(--muted); }}
    @media (max-width:760px) {{ .candidate-copy,.diagrams {{ grid-template-columns:1fr; }} .candidate-header {{ display:block; }} .strength {{ display:inline-block; margin-bottom:16px; }} .evidence-list li {{ grid-template-columns:1fr; }} }}
    @media (prefers-color-scheme:dark) {{ :root {{ --paper:#111317; --card:#181b20; --ink:#f5f3ed; --muted:#a8b0bd; --line:#353b45; --blue:#8aa7ff; }} .strength-strong {{ background:#153e32; color:#8ee6c4; }} .strength-worth_exploring {{ background:#493516; color:#ffd589; }} .strength-speculative {{ background:#30343b; color:#d0d5dd; }} .architecture-graph rect {{ fill:#25304d; }} .architecture-graph .kind-adapter rect {{ fill:#173d33; }} .architecture-graph .kind-external rect,.architecture-graph .kind-dependency rect {{ fill:#493516; }} }}
    @media print {{ body {{ background:#fff; color:#111; }} main {{ width:100%; padding:0; }} .candidate {{ break-inside:avoid; box-shadow:none; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <p class="eyebrow">EZPowers · Architecture review</p>
    <h1>Deepening opportunities in {html.escape(repository['name'])}</h1>
    <p class="lede">{html.escape(report['scope'])}</p>
    <p>{html.escape(report['scope_rationale'])}</p>
    <div class="meta">
      <span>Revision: {html.escape(repository['revision'])}</span>
      <span>{html.escape(dirty)}</span>
      <span>Scope basis: {html.escape(scope_basis)}</span>
      <span>Generated: {html.escape(report['generated_at'])}</span>
      <span>{len(report['candidates'])} candidates</span>
    </div>
  </header>
  <section class="top-recommendation">
    <p class="eyebrow">Top recommendation</p>
    <h2><a href="#{html.escape(top_candidate['id'])}">{html.escape(top_candidate['title'])}</a></h2>
    <h3>Why this candidate</h3>
    <p>{html.escape(top_recommendation['rationale'])}</p>
  </section>
  {''.join(candidate_parts)}
  <footer>This local advisory report uses no network resources and is not EZPowers completion evidence.</footer>
</main>
</body>
</html>
"""


def _read_input(path: Path) -> tuple[Any, str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ReportError(f"cannot read input JSON: {exc}") from exc
    if len(raw) > MAX_INPUT_BYTES:
        raise ReportError(f"input exceeds {MAX_INPUT_BYTES} bytes")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReportError(f"cannot read input JSON: {exc}") from exc
    return value, hashlib.sha256(raw).hexdigest()


def _output_path(raw: str | None, project_root: Path) -> Path:
    if raw is None:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        result = (
            Path(tempfile.gettempdir())
            / f"ezpowers-architecture-review-{stamp}-{uuid.uuid4().hex[:8]}.html"
        ).resolve()
    else:
        result = Path(raw).expanduser().resolve()
    if result.suffix.lower() != ".html":
        raise ReportError("output must use the .html extension")
    if _within(result, project_root):
        raise ReportError("output must be outside the project root")
    if result.exists():
        raise ReportError(f"output already exists: {result}")
    if not result.parent.is_dir():
        raise ReportError(f"output parent does not exist: {result.parent}")
    return result


def _atomic_write(path: Path, content: str) -> None:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            temp_path = Path(stream.name)
        try:
            os.link(temp_path, path)
        except FileExistsError as exc:
            raise ReportError(f"output already exists: {path}") from exc
        temp_path.unlink()
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_fingerprint(
    report: dict[str, Any],
    project_root: Path,
) -> tuple[str, int]:
    relative_paths = sorted(
        {
            path
            for candidate in report["candidates"]
            for path in (
                candidate["files"]
                + [item["path"] for item in candidate["evidence"]]
                + candidate["adr"]["references"]
            )
        }
    )
    digest = hashlib.sha256()
    for relative_path in relative_paths:
        source = project_root / Path(*PurePosixPath(relative_path).parts)
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        with source.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest(), len(relative_paths)


def render(
    *,
    project_root: Path,
    input_path: Path,
    output: str | None,
    open_report: bool,
) -> dict[str, Any]:
    root = project_root.expanduser().resolve()
    if not root.is_dir():
        raise ReportError(f"project root does not exist: {root}")
    resolved_input = input_path.expanduser().resolve()
    input_value, input_sha256 = _read_input(resolved_input)
    report = validate_report(input_value, root)
    source_sha256, source_file_count = _source_fingerprint(report, root)
    output_path = _output_path(output, root)
    _atomic_write(output_path, render_html(report))
    warnings: list[str] = []
    opened = False
    if open_report:
        try:
            opened = bool(webbrowser.open_new_tab(output_path.as_uri()))
        except (OSError, webbrowser.Error) as exc:
            warnings.append(f"browser open failed: {exc}")
        if not opened and not warnings:
            warnings.append("browser open request was not accepted")
    return {
        "status": "PASS_WITH_WARNING" if warnings else "PASS",
        "schema_version": SCHEMA_VERSION,
        "report_path": str(output_path),
        "report_sha256": _sha256(output_path),
        "input_sha256": input_sha256,
        "source_sha256": source_sha256,
        "source_file_count": source_file_count,
        "candidate_count": len(report["candidates"]),
        "opened": opened,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output")
    parser.add_argument("--open", action="store_true", dest="open_report")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    try:
        result = render(
            project_root=args.project_root,
            input_path=args.input,
            output=args.output,
            open_report=args.open_report,
        )
    except (OSError, ReportError) as exc:
        payload = {"status": "ERROR", "error": str(exc)}
        if args.json_output:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print(f"ERROR: {exc}")
        return 2
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(f"{result['status']}: {result['report_path']}")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
