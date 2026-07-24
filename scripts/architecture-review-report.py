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


SCHEMA_VERSION = 1
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
        nodes.append(
            {
                "id": node_id,
                "label": _text(node["label"], f"{node_label}.label", MAX_LABEL),
                "layer": layer,
                "kind": kind,
            }
        )
    edges: list[dict[str, str]] = []
    for index, raw_edge in enumerate(raw_edges):
        edge_label = f"{label}.edges[{index}]"
        edge = _require_object(raw_edge, edge_label)
        _require_keys(
            edge,
            required={"from", "to"},
            optional={"label"},
            label=edge_label,
        )
        source = _identifier(edge["from"], f"{edge_label}.from")
        target = _identifier(edge["to"], f"{edge_label}.to")
        if source not in node_ids or target not in node_ids:
            raise ReportError(f"{edge_label} has a dangling endpoint")
        edges.append(
            {
                "from": source,
                "to": target,
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
            "generated_at",
            "top_recommendation_id",
            "candidates",
        },
        optional={"language"},
        label="report",
    )
    if report["schema_version"] != SCHEMA_VERSION:
        raise ReportError("schema_version must be 1")
    language = report.get("language", "en")
    if not isinstance(language, str) or LANGUAGE_RE.fullmatch(language) is None:
        raise ReportError("language must be a BCP-47-style language tag")
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
        for evidence_index, raw_item in enumerate(raw_evidence):
            item_label = f"{label}.evidence[{evidence_index}]"
            item = _require_object(raw_item, item_label)
            _require_keys(
                item,
                required={"path", "finding"},
                optional={"line"},
                label=item_label,
            )
            line = item.get("line")
            if line is not None and (
                isinstance(line, bool) or not isinstance(line, int) or line < 1
            ):
                raise ReportError(f"{item_label}.line must be a positive integer")
            evidence.append(
                {
                    "path": _repo_path(
                        item["path"],
                        f"{item_label}.path",
                        project_root,
                        file_only=True,
                    ),
                    "line": line,
                    "finding": _text(item["finding"], f"{item_label}.finding"),
                }
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
                "before": _validate_graph(candidate["before"], f"{label}.before"),
                "after": _validate_graph(candidate["after"], f"{label}.after"),
            }
        )
    top_id = _identifier(report["top_recommendation_id"], "top_recommendation_id")
    if top_id not in candidate_ids:
        raise ReportError("top_recommendation_id does not identify a candidate")
    return {
        "schema_version": SCHEMA_VERSION,
        "language": language,
        "repository": clean_repository,
        "scope": _text(report["scope"], "scope"),
        "generated_at": _validate_timestamp(report["generated_at"]),
        "top_recommendation_id": top_id,
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
                f'<g class="graph-node kind-{node["kind"]}">'
                f"<title>{html.escape(node['label'])}</title>"
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{node_width:.1f}" '
                f'height="{node_height}" rx="12"></rect>'
                f'<text x="{x + node_width / 2:.1f}" y="{y + 32:.1f}" '
                f'text-anchor="middle">{html.escape(visible)}</text></g>'
            )
    marker_id = f"arrow-{prefix}"
    edge_parts: list[str] = []
    for edge in graph["edges"]:
        source_x, source_y = positions[edge["from"]]
        target_x, target_y = positions[edge["to"]]
        edge_parts.append(
            f'<line x1="{source_x:.1f}" y1="{source_y + node_height / 2:.1f}" '
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
        f'<desc id="{prefix}-desc">Layered module and dependency diagram.</desc>'
        f"<defs><marker id=\"{marker_id}\" viewBox=\"0 0 10 10\" refX=\"9\" refY=\"5\" "
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z"></path></marker></defs>'
        + "".join(edge_parts)
        + "".join(node_parts)
        + "</svg>"
    )


def render_html(report: dict[str, Any]) -> str:
    repository = report["repository"]
    candidate_parts: list[str] = []
    for index, candidate in enumerate(report["candidates"], 1):
        top = candidate["id"] == report["top_recommendation_id"]
        evidence_items = "".join(
            "<li><code>"
            + html.escape(item["path"])
            + (f":{item['line']}" if item["line"] is not None else "")
            + "</code><span>"
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
            + "</article>"
        )
    dirty = "dirty working tree" if repository["dirty"] else "clean working tree"
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
    .evidence-list li {{ display:grid; grid-template-columns:minmax(160px,.45fr) 1fr; gap:14px; border-top:1px solid var(--line); padding-top:9px; }}
    .evidence-list code {{ overflow-wrap:anywhere; color:var(--blue); }}
    .architecture-graph {{ width:100%; height:auto; border:1px solid var(--line); border-radius:16px; background:var(--paper); }}
    .architecture-graph line {{ stroke:#7b8494; stroke-width:2; }}
    .architecture-graph marker path {{ fill:#7b8494; }}
    .architecture-graph rect {{ fill:#eef2ff; stroke:#7086c7; stroke-width:1.5; }}
    .architecture-graph .kind-adapter rect {{ fill:#dff7ed; stroke:#45a783; }}
    .architecture-graph .kind-external rect,.architecture-graph .kind-dependency rect {{ fill:#fff0d6; stroke:#c88a33; }}
    .architecture-graph text {{ fill:var(--ink); font-size:13px; font-weight:650; }}
    .architecture-graph .edge-label {{ font-size:10px; font-weight:500; fill:var(--muted); paint-order:stroke; stroke:var(--paper); stroke-width:4px; }}
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
    <div class="meta">
      <span>Revision: {html.escape(repository['revision'])}</span>
      <span>{html.escape(dirty)}</span>
      <span>Generated: {html.escape(report['generated_at'])}</span>
      <span>{len(report['candidates'])} candidates</span>
    </div>
  </header>
  {''.join(candidate_parts)}
  <footer>This local advisory report uses no network resources and is not EZPowers completion evidence.</footer>
</main>
</body>
</html>
"""


def _read_input(path: Path) -> Any:
    if not path.is_file():
        raise ReportError(f"input file does not exist: {path}")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ReportError(f"input exceeds {MAX_INPUT_BYTES} bytes")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReportError(f"cannot read input JSON: {exc}") from exc


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
    report = validate_report(_read_input(input_path.expanduser().resolve()), root)
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
        "report_path": str(output_path),
        "report_sha256": _sha256(output_path),
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
