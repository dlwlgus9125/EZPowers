#!/usr/bin/env python3
"""Offline DESIGN.md profile validator and change reviewer for EZPowers.

The implementation is intentionally standard-library only. It implements the
document subset recorded in the installed EZPowers profile; it is not a copy
or a claim of complete compatibility with the upstream Google CLI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Iterable


SCHEMA_VERSION = 1
DEFAULT_PROFILE = "google-alpha-0.4.0-ezpowers-1"
MAX_FILE_BYTES = 2_000_000
FRONTEND_START = "<!-- ezpowers:frontend-design:start -->"
FRONTEND_END = "<!-- ezpowers:frontend-design:end -->"
RESERVED_PATH_PARTS = {
    ".git",
    ".ezpowers",
    ".agents",
    ".claude",
    ".cache",
    "node_modules",
    "dist",
    "build",
    "target",
}
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}
TOKEN_GROUPS = ("colors", "typography", "rounded", "spacing", "components")
REF_RE = re.compile(r"\{([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+)\}")
HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
DIMENSION_RE = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)(px|em|rem)$", re.I)
CSS_COLOR_RE = re.compile(
    r"^(?:[A-Za-z]+|(?:rgb|rgba|hsl|hsla|hwb|oklch|oklab|lch|lab|color-mix)\(.+\))$",
    re.I,
)


class InputError(RuntimeError):
    """The command could not safely load its requested input or profile."""


class YamlSubsetError(ValueError):
    """The DESIGN.md frontmatter is outside the deterministic YAML subset."""


@dataclass(frozen=True)
class YamlLine:
    indent: int
    content: str
    number: int


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_bytes(path: pathlib.Path, label: str) -> bytes:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise InputError(f"cannot read {label} {path}: {exc}") from exc
    if len(data) > MAX_FILE_BYTES:
        raise InputError(f"{label} exceeds {MAX_FILE_BYTES} bytes: {path}")
    return data


def decode_utf8(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InputError(f"{label} must be UTF-8: {exc}") from exc


def profile_candidates() -> list[pathlib.Path]:
    script = pathlib.Path(__file__).resolve()
    candidates = [
        script.parent.parent / "docs" / "reference" / "design-md-profile.json",
        script.parent.parent / "contracts" / "design-md-profile.json",
    ]
    return list(dict.fromkeys(path.resolve() for path in candidates))


def load_profile(
    profile_id: str = DEFAULT_PROFILE,
    profile_path: pathlib.Path | None = None,
) -> tuple[dict[str, Any], pathlib.Path]:
    candidates = [profile_path.resolve()] if profile_path else profile_candidates()
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        looked = ", ".join(str(candidate) for candidate in candidates)
        raise InputError(f"DESIGN.md profile contract not found; looked in: {looked}")
    data = read_bytes(path, "profile")
    try:
        document = json.loads(decode_utf8(data, "profile"))
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid DESIGN.md profile JSON: {exc}") from exc
    if not isinstance(document, dict) or document.get("schema_version") != SCHEMA_VERSION:
        raise InputError("DESIGN.md profile schema_version must be 1")
    profiles = document.get("profiles")
    if not isinstance(profiles, dict) or not isinstance(profiles.get(profile_id), dict):
        raise InputError(f"unknown DESIGN.md validator profile: {profile_id}")
    profile = dict(profiles[profile_id])
    profile["id"] = profile_id
    profile["contract_sha256"] = sha256_bytes(data)
    return profile, path


def strip_inline_comment(value: str) -> str:
    single = False
    double = False
    escaped = False
    for index, character in enumerate(value):
        if escaped:
            escaped = False
            continue
        if character == "\\" and double:
            escaped = True
            continue
        if character == "'" and not double:
            single = not single
        elif character == '"' and not single:
            double = not double
        elif character == "#" and not single and not double and index > 0 and value[index - 1].isspace():
            return value[:index].rstrip()
    return value.rstrip()


def parse_scalar(raw: str, line_number: int) -> Any:
    value = strip_inline_comment(raw.strip())
    if not value:
        return ""
    if value.startswith("!") or re.search(r"(?:^|\s)[&*][A-Za-z0-9_-]+", value):
        raise YamlSubsetError(f"line {line_number}: YAML tags, anchors, and aliases are not supported")
    if value in {"|", ">", "|-", ">-", "|+", ">+"}:
        raise YamlSubsetError(f"line {line_number}: multiline YAML scalars are not supported")
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise YamlSubsetError(f"line {line_number}: invalid quoted string: {exc.msg}") from exc
        if not isinstance(parsed, str):
            raise YamlSubsetError(f"line {line_number}: expected a quoted string")
        return parsed
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise YamlSubsetError(f"line {line_number}: unterminated single-quoted string")
        return value[1:-1].replace("''", "'")
    if value.startswith("[") or value.startswith("{"):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise YamlSubsetError(
                f"line {line_number}: flow collections must use JSON syntax: {exc.msg}"
            ) from exc
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "~"}:
        return None
    if re.fullmatch(r"-?(?:0|[1-9]\d*)", value):
        return int(value)
    if re.fullmatch(r"-?(?:0|[1-9]\d*)\.\d+", value):
        return float(value)
    return value


def split_mapping(content: str, line_number: int) -> tuple[str, str]:
    single = False
    double = False
    escaped = False
    for index, character in enumerate(content):
        if escaped:
            escaped = False
            continue
        if character == "\\" and double:
            escaped = True
            continue
        if character == "'" and not double:
            single = not single
        elif character == '"' and not single:
            double = not double
        elif character == ":" and not single and not double:
            raw_key = content[:index].strip()
            raw_value = content[index + 1 :]
            if not raw_key:
                break
            if raw_key.startswith(('"', "'")):
                key = parse_scalar(raw_key, line_number)
            else:
                key = raw_key
            if not isinstance(key, str) or not key or any(char in key for char in "{}[]"):
                raise YamlSubsetError(f"line {line_number}: invalid mapping key")
            if key == "<<":
                raise YamlSubsetError(f"line {line_number}: YAML merge keys are not supported")
            return key, raw_value.strip()
    raise YamlSubsetError(f"line {line_number}: expected a key/value mapping")


def yaml_lines(frontmatter: str) -> list[YamlLine]:
    result: list[YamlLine] = []
    for number, raw in enumerate(frontmatter.splitlines(), 2):
        if "\t" in raw[: len(raw) - len(raw.lstrip(" \t"))]:
            raise YamlSubsetError(f"line {number}: tabs are not allowed for indentation")
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        result.append(YamlLine(indent, raw[indent:].rstrip(), number))
    return result


def parse_yaml_subset(frontmatter: str) -> dict[str, Any]:
    lines = yaml_lines(frontmatter)
    if not lines:
        return {}
    if lines[0].indent != 0:
        raise YamlSubsetError(f"line {lines[0].number}: top-level keys must not be indented")

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(lines) or lines[index].indent != indent:
            raise YamlSubsetError("invalid YAML indentation")
        is_list = lines[index].content == "-" or lines[index].content.startswith("- ")
        container: Any = [] if is_list else {}
        while index < len(lines):
            line = lines[index]
            if line.indent < indent:
                break
            if line.indent > indent:
                raise YamlSubsetError(f"line {line.number}: unexpected indentation")
            line_is_list = line.content == "-" or line.content.startswith("- ")
            if line_is_list != is_list:
                raise YamlSubsetError(f"line {line.number}: cannot mix list and mapping entries")
            if is_list:
                rest = line.content[1:].strip()
                index += 1
                if not rest:
                    if index >= len(lines) or lines[index].indent <= indent:
                        raise YamlSubsetError(f"line {line.number}: empty list item")
                    item, index = parse_block(index, lines[index].indent)
                elif ":" in rest and not rest.startswith(('"', "'", "{", "[")):
                    key, raw_value = split_mapping(rest, line.number)
                    item = {}
                    if raw_value:
                        item[key] = parse_scalar(raw_value, line.number)
                    elif index < len(lines) and lines[index].indent > indent:
                        item[key], index = parse_block(index, lines[index].indent)
                    else:
                        item[key] = {}
                    if index < len(lines) and lines[index].indent > indent:
                        extra_indent = lines[index].indent
                        extra, index = parse_block(index, extra_indent)
                        if not isinstance(extra, dict):
                            raise YamlSubsetError(
                                f"line {lines[index - 1].number}: list mapping continuation must be a mapping"
                            )
                        for extra_key, extra_value in extra.items():
                            if extra_key in item:
                                raise YamlSubsetError(
                                    f"line {line.number}: duplicate key in list item: {extra_key}"
                                )
                            item[extra_key] = extra_value
                else:
                    item = parse_scalar(rest, line.number)
                container.append(item)
                continue

            key, raw_value = split_mapping(line.content, line.number)
            if key in container:
                raise YamlSubsetError(f"line {line.number}: duplicate mapping key: {key}")
            index += 1
            if raw_value:
                container[key] = parse_scalar(raw_value, line.number)
            elif index < len(lines) and lines[index].indent > indent:
                container[key], index = parse_block(index, lines[index].indent)
            else:
                container[key] = {}
        return container, index

    value, final_index = parse_block(0, 0)
    if final_index != len(lines) or not isinstance(value, dict):
        raise YamlSubsetError("frontmatter root must be a mapping")
    return value


def split_design_document(text: str) -> tuple[dict[str, Any], str, bool]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.startswith("---\n"):
        return {}, normalized, False
    end = normalized.find("\n---\n", 4)
    if end < 0:
        raise YamlSubsetError("frontmatter opening delimiter has no closing delimiter")
    frontmatter = normalized[4:end]
    return parse_yaml_subset(frontmatter), normalized[end + 5 :], True


def finding(severity: str, rule: str, path: str, message: str) -> dict[str, str]:
    return {"severity": severity, "rule": rule, "path": path, "message": message}


def add(
    findings: list[dict[str, str]],
    severity: str,
    rule: str,
    path: str,
    message: str,
) -> None:
    findings.append(finding(severity, rule, path, message))


def omitted_sections(value: Any, findings: list[dict[str, str]]) -> set[str]:
    if value is None:
        return set()
    if not isinstance(value, list):
        add(findings, "error", "omitted-rules", "frontmatter.omitted", "omitted must be an array")
        return set()
    result: set[str] = set()
    for index, item in enumerate(value):
        section: Any
        if isinstance(item, str):
            section = item
        elif isinstance(item, dict):
            section = item.get("section")
            if set(item) - {"section", "reason"}:
                add(
                    findings,
                    "warning",
                    "unknown-key",
                    f"frontmatter.omitted[{index}]",
                    "omitted entry contains an unknown key",
                )
            reason = item.get("reason")
            if reason is not None and not isinstance(reason, str):
                add(
                    findings,
                    "error",
                    "omitted-rules",
                    f"frontmatter.omitted[{index}].reason",
                    "omission reason must be a string",
                )
        else:
            section = None
        if not isinstance(section, str) or not section.strip():
            add(
                findings,
                "error",
                "omitted-rules",
                f"frontmatter.omitted[{index}]",
                "omitted entry must name a section",
            )
            continue
        result.add(section.strip().lower())
    return result


def is_dimension(value: Any, *, allow_number: bool = False) -> bool:
    if allow_number and isinstance(value, (int, float)) and not isinstance(value, bool):
        return math.isfinite(float(value))
    return isinstance(value, str) and DIMENSION_RE.fullmatch(value.strip()) is not None


def is_color(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX_RE.fullmatch(value.strip()) or CSS_COLOR_RE.fullmatch(value.strip()))


def flatten(value: Any, prefix: tuple[str, ...] = ()) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            result.update(flatten(child, (*prefix, str(key))))
    elif prefix:
        result[".".join(prefix)] = value
    return result


def path_value(tree: dict[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = tree
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def referenced_paths(value: Any) -> Iterable[tuple[str, str]]:
    for path, leaf in flatten(value).items():
        if isinstance(leaf, str):
            for match in REF_RE.finditer(leaf):
                yield path, match.group(1)


def resolve_reference(tree: dict[str, Any], value: Any, seen: set[str] | None = None) -> Any:
    if not isinstance(value, str):
        return value
    match = re.fullmatch(REF_RE, value.strip())
    if not match:
        return value
    ref = match.group(1)
    seen = set() if seen is None else set(seen)
    if ref in seen:
        return None
    seen.add(ref)
    exists, target = path_value(tree, ref)
    if not exists:
        return None
    return resolve_reference(tree, target, seen)


def parse_hex_color(value: Any) -> tuple[float, float, float] | None:
    if not isinstance(value, str) or not HEX_RE.fullmatch(value.strip()):
        return None
    raw = value.strip()[1:]
    if len(raw) in {3, 4}:
        raw = "".join(character * 2 for character in raw)
    if len(raw) == 8:
        raw = raw[:6]
    return tuple(int(raw[index : index + 2], 16) / 255 for index in (0, 2, 4))  # type: ignore[return-value]


def contrast_ratio(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    def luminance(rgb: tuple[float, float, float]) -> float:
        values = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in rgb]
        return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]

    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def markdown_sections(body: str) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    fence: str | None = None
    for number, line in enumerate(body.splitlines(), 1):
        stripped = line.lstrip()
        fence_match = re.match(r"^(```+|~~~+)", stripped)
        if fence_match:
            marker = fence_match.group(1)[0]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            continue
        if fence is None:
            match = re.match(r"^##\s+(.+?)\s*#*\s*$", line)
            if match:
                result.append((match.group(1).strip(), number))
    return result


def validate_tokens(
    tree: dict[str, Any],
    profile: dict[str, Any],
    findings: list[dict[str, str]],
) -> None:
    frontmatter_profile = profile.get("frontmatter", {})
    allowed = set(frontmatter_profile.get("allowed_groups", []))
    for key in sorted(set(tree) - allowed):
        add(findings, "warning", "unknown-key", f"frontmatter.{key}", "unknown top-level key is preserved")

    if tree and (not isinstance(tree.get("name"), str) or not tree.get("name", "").strip()):
        add(findings, "error", "unknown-key", "frontmatter.name", "name must be a non-empty string")
    if "version" in tree and tree.get("version") != profile.get("format_version"):
        add(
            findings,
            "warning",
            "unknown-key",
            "frontmatter.version",
            f"profile expects format version {profile.get('format_version')!r}",
        )
    if "description" in tree and not isinstance(tree.get("description"), str):
        add(findings, "error", "unknown-key", "frontmatter.description", "description must be a string")

    omitted = omitted_sections(tree.get("omitted"), findings)
    colors = tree.get("colors")
    if colors is None:
        if "colors" not in omitted:
            add(findings, "warning", "missing-sections", "frontmatter.colors", "colors are missing and not intentionally omitted")
    elif not isinstance(colors, dict) or not colors:
        add(findings, "error", "unknown-key", "frontmatter.colors", "colors must be a non-empty mapping")
    else:
        if "primary" not in colors:
            add(findings, "warning", "missing-primary", "frontmatter.colors", "colors should define a primary token")
        for name, value in colors.items():
            if not is_color(value) and not (isinstance(value, str) and re.fullmatch(REF_RE, value.strip())):
                add(findings, "error", "unknown-key", f"frontmatter.colors.{name}", "color must be a CSS color or token reference")

    typography = tree.get("typography")
    typography_properties = set(frontmatter_profile.get("typography_properties", []))
    if typography is None:
        if "typography" not in omitted:
            add(findings, "warning", "missing-typography", "frontmatter.typography", "typography is missing and not intentionally omitted")
    elif not isinstance(typography, dict) or not typography:
        add(findings, "error", "unknown-key", "frontmatter.typography", "typography must be a non-empty mapping")
    else:
        for token, raw in typography.items():
            base = f"frontmatter.typography.{token}"
            if not isinstance(raw, dict) or not raw:
                add(findings, "error", "unknown-key", base, "typography token must be a non-empty mapping")
                continue
            for prop in sorted(set(raw) - typography_properties):
                add(findings, "warning", "unknown-key", f"{base}.{prop}", "unknown typography property is preserved")
            for prop in ("fontFamily", "fontFeature", "fontVariation"):
                if prop in raw and not isinstance(raw[prop], str):
                    add(findings, "error", "unknown-key", f"{base}.{prop}", f"{prop} must be a string")
            for prop in ("fontSize", "letterSpacing"):
                if prop in raw and not is_dimension(raw[prop]):
                    add(findings, "error", "unknown-key", f"{base}.{prop}", f"{prop} must use px, em, or rem")
            if "fontWeight" in raw and not (
                isinstance(raw["fontWeight"], (int, float, str)) and not isinstance(raw["fontWeight"], bool)
            ):
                add(findings, "error", "unknown-key", f"{base}.fontWeight", "fontWeight must be numeric or a numeric string")
            if "lineHeight" in raw and not is_dimension(raw["lineHeight"], allow_number=True):
                add(findings, "error", "unknown-key", f"{base}.lineHeight", "lineHeight must be a dimension or number")

    for group in ("rounded", "spacing"):
        value = tree.get(group)
        if value is None:
            if group not in omitted:
                add(findings, "warning", "missing-sections", f"frontmatter.{group}", f"{group} is missing and not intentionally omitted")
            continue
        if not isinstance(value, dict) or not value:
            add(findings, "error", "unknown-key", f"frontmatter.{group}", f"{group} must be a non-empty mapping")
            continue
        for name, item in value.items():
            allow_number = group == "spacing"
            if not is_dimension(item, allow_number=allow_number) and not (
                isinstance(item, str) and re.fullmatch(REF_RE, item.strip())
            ):
                severity = "warning" if group == "spacing" and isinstance(item, str) else "error"
                add(findings, severity, "unknown-key", f"frontmatter.{group}.{name}", f"{group} token is not a recognised dimension")

    components = tree.get("components")
    component_properties = set(frontmatter_profile.get("component_properties", []))
    if components is None:
        if "components" not in omitted:
            add(findings, "warning", "missing-sections", "frontmatter.components", "components are missing and not intentionally omitted")
    elif not isinstance(components, dict) or not components:
        add(findings, "error", "unknown-key", "frontmatter.components", "components must be a non-empty mapping")
    else:
        for component, raw in components.items():
            base = f"frontmatter.components.{component}"
            if not isinstance(raw, dict) or not raw:
                add(findings, "error", "unknown-key", base, "component token must be a non-empty mapping")
                continue
            for prop, item in raw.items():
                if prop not in component_properties:
                    add(findings, "warning", "unknown-key", f"{base}.{prop}", "unknown component property is preserved")
                if isinstance(item, (dict, list)) or item is None or isinstance(item, bool):
                    add(findings, "error", "unknown-key", f"{base}.{prop}", "component property must be a string or number")

    all_flat = flatten(tree)
    graph: dict[str, list[str]] = {}
    referenced: set[str] = set()
    for source, reference in referenced_paths(tree):
        exists, target = path_value(tree, reference)
        if not exists:
            add(findings, "error", "broken-ref", f"frontmatter.{source}", f"token reference does not exist: {reference}")
            continue
        if source.startswith("components.") or not isinstance(target, dict):
            graph.setdefault(source, []).append(reference)
            referenced.add(reference)
        else:
            add(findings, "error", "broken-ref", f"frontmatter.{source}", f"reference must resolve to a primitive token: {reference}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, trail: list[str]) -> None:
        if node in visiting:
            cycle = " -> ".join((*trail, node))
            add(findings, "error", "broken-ref", f"frontmatter.{node}", f"circular token reference: {cycle}")
            return
        if node in visited:
            return
        visiting.add(node)
        for child in graph.get(node, []):
            visit(child, [*trail, node])
        visiting.discard(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node, [])

    for path in sorted(all_flat):
        if path.split(".", 1)[0] in TOKEN_GROUPS and path not in referenced and not path.startswith("components."):
            add(findings, "info", "orphaned-tokens", f"frontmatter.{path}", "token is not referenced by another machine-readable token")

    if isinstance(components, dict):
        for component, raw in components.items():
            if not isinstance(raw, dict):
                continue
            background = parse_hex_color(resolve_reference(tree, raw.get("backgroundColor")))
            foreground = parse_hex_color(resolve_reference(tree, raw.get("textColor")))
            if background and foreground:
                ratio = contrast_ratio(background, foreground)
                if ratio < 4.5:
                    add(
                        findings,
                        "warning",
                        "contrast-ratio",
                        f"frontmatter.components.{component}",
                        f"text/background contrast is {ratio:.2f}:1; normal text guidance is 4.5:1",
                    )

    token_count = sum(1 for path in all_flat if path.split(".", 1)[0] in TOKEN_GROUPS)
    add(findings, "info", "token-summary", "frontmatter", f"validated {token_count} token values")


def validate_sections(
    body: str,
    profile: dict[str, Any],
    tree: dict[str, Any],
    findings: list[dict[str, str]],
) -> list[str]:
    sections = markdown_sections(body)
    seen_headings: dict[str, int] = {}
    for heading, line in sections:
        normalized = heading.casefold()
        if normalized in seen_headings:
            add(findings, "error", "section-order", f"body.line:{line}", f"duplicate section heading: {heading}")
        else:
            seen_headings[normalized] = line

    aliases: dict[str, tuple[str, int]] = {}
    ordered_names: list[str] = []
    for index, raw in enumerate(profile.get("sections", [])):
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            continue
        name = raw["name"]
        ordered_names.append(name)
        aliases[name.casefold()] = (name, index)
        for alias in raw.get("aliases", []):
            if isinstance(alias, str):
                aliases[alias.casefold()] = (name, index)
    canonical_present: list[tuple[str, int, int]] = []
    canonical_seen: dict[str, int] = {}
    for heading, line in sections:
        resolved = aliases.get(heading.casefold())
        if resolved is None:
            add(findings, "info", "unknown-section", f"body.line:{line}", f"unknown section is preserved: {heading}")
            continue
        name, order = resolved
        if name in canonical_seen:
            add(findings, "error", "section-order", f"body.line:{line}", f"duplicate canonical section: {name}")
        canonical_seen[name] = line
        canonical_present.append((name, order, line))
    orders = [item[1] for item in canonical_present]
    if orders != sorted(orders):
        add(findings, "warning", "section-order", "body", "known sections are not in canonical order")

    omitted = omitted_sections(tree.get("omitted"), [])
    group_to_section = {
        "colors": "Colors",
        "typography": "Typography",
        "spacing": "Layout",
        "rounded": "Shapes",
        "components": "Components",
    }
    for group, section in group_to_section.items():
        if group in tree and section not in canonical_seen and group not in omitted:
            add(findings, "warning", "missing-sections", "body", f"token group {group} has no {section} section")
    if not sections:
        add(findings, "warning", "missing-sections", "body", "DESIGN.md has no level-two guidance sections")
    return [heading for heading, _line in sections]


def validate_token_like_prose(
    body: str,
    tree: dict[str, Any],
    findings: list[dict[str, str]],
) -> None:
    """Flag machine-looking token declarations that prose parsers ignore."""
    known_names = {
        name
        for group in TOKEN_GROUPS
        for name in (tree.get(group, {}) if isinstance(tree.get(group), dict) else {})
    }
    fence: str | None = None
    for number, line in enumerate(body.splitlines(), 1):
        stripped = line.strip()
        fence_match = re.match(r"^(```+|~~~+)", stripped)
        if fence_match:
            marker = fence_match.group(1)[0]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            continue
        if fence is not None:
            continue
        match = re.match(
            r"^(?:[-*]\s+)?(?:`)?--?(?P<name>[A-Za-z][A-Za-z0-9_-]*)(?:`)?\s*:\s*(?:#[0-9A-Fa-f]{3,8}|-?(?:\d+(?:\.\d+)?|\.\d+)(?:px|em|rem))\b",
            stripped,
        )
        if match and match.group("name") not in known_names:
            add(
                findings,
                "info",
                "token-like-ignored",
                f"body.line:{number}",
                f"token-like prose is not machine-readable: {match.group('name')}",
            )


def lint_text(
    text: str,
    *,
    profile: dict[str, Any],
    label: str,
    digest: str,
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    tree: dict[str, Any] = {}
    body = text
    has_frontmatter = False
    try:
        tree, body, has_frontmatter = split_design_document(text)
    except YamlSubsetError as exc:
        add(findings, "error", "yaml-subset", "frontmatter", str(exc))
    if not has_frontmatter:
        add(findings, "warning", "missing-sections", "frontmatter", "machine-readable design tokens are absent")
    if not findings or all(item["rule"] != "yaml-subset" for item in findings):
        validate_tokens(tree, profile, findings)
    section_names = validate_sections(body, profile, tree, findings)
    validate_token_like_prose(body, tree, findings)
    findings.sort(key=lambda item: (SEVERITY_ORDER[item["severity"]], item["rule"], item["path"], item["message"]))
    counts = {severity: sum(item["severity"] == severity for item in findings) for severity in SEVERITY_ORDER}
    status = "PASS" if counts["error"] == 0 else "FAIL"
    tokens = {group: tree.get(group, {}) for group in TOKEN_GROUPS if group in tree}
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "profile": profile["id"],
        "profile_contract_sha256": profile["contract_sha256"],
        "file": label,
        "sha256": digest,
        "has_frontmatter": has_frontmatter,
        "sections": section_names,
        "tokens": tokens,
        "findings": findings,
        "summary": counts,
    }


def lint_path(
    path: pathlib.Path,
    profile_id: str = DEFAULT_PROFILE,
    profile_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    profile, _ = load_profile(profile_id, profile_path)
    data = read_bytes(path, "DESIGN.md")
    text = decode_utf8(data, "DESIGN.md")
    return lint_text(text, profile=profile, label=path.as_posix(), digest=sha256_bytes(data))


def token_changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    old = flatten(before)
    new = flatten(after)
    return {
        "added": [{"path": key, "value": new[key]} for key in sorted(set(new) - set(old))],
        "removed": [{"path": key, "value": old[key]} for key in sorted(set(old) - set(new))],
        "modified": [
            {"path": key, "before": old[key], "after": new[key]}
            for key in sorted(set(old) & set(new))
            if old[key] != new[key]
        ],
    }


def diff_paths(
    before_path: pathlib.Path,
    after_path: pathlib.Path,
    profile_id: str = DEFAULT_PROFILE,
    profile_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    before = lint_path(before_path, profile_id, profile_path)
    after = lint_path(after_path, profile_id, profile_path)
    changes = token_changes(before.get("tokens", {}), after.get("tokens", {}))
    before_sections = before.get("sections", [])
    after_sections = after.get("sections", [])
    before_findings = {
        (item["severity"], item["rule"], item["path"], item["message"]): item
        for item in before.get("findings", [])
        if isinstance(item, dict)
    }
    after_findings = {
        (item["severity"], item["rule"], item["path"], item["message"]): item
        for item in after.get("findings", [])
        if isinstance(item, dict)
    }
    added_findings = [
        after_findings[key] for key in sorted(set(after_findings) - set(before_findings))
    ]
    resolved_findings = [
        before_findings[key] for key in sorted(set(before_findings) - set(after_findings))
    ]
    reasons: list[str] = []
    if after["status"] != "PASS":
        reasons.append("invalid-after")
    if changes["removed"]:
        reasons.append("removed-token")
    if any(item["severity"] == "error" for item in added_findings):
        reasons.append("new-error")
    if any(item["severity"] == "warning" for item in added_findings):
        reasons.append("new-warning")
    regression = bool(reasons)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "REGRESSION" if regression else "PASS",
        "profile": profile_id,
        "before": {"file": before["file"], "sha256": before["sha256"], "summary": before["summary"]},
        "after": {"file": after["file"], "sha256": after["sha256"], "summary": after["summary"]},
        "tokens": changes,
        "sections": {
            "added": [item for item in after_sections if item not in before_sections],
            "removed": [item for item in before_sections if item not in after_sections],
            "order_changed": [item for item in before_sections if item in after_sections]
            != [item for item in after_sections if item in before_sections],
        },
        "finding_delta": {
            severity: after["summary"][severity] - before["summary"][severity]
            for severity in SEVERITY_ORDER
        },
        "findings": {
            "added": added_findings,
            "resolved": resolved_findings,
        },
        "regression_reasons": reasons,
    }


def safe_relative_path(
    root: pathlib.Path,
    value: str,
    *,
    label: str,
    must_exist: bool = False,
) -> tuple[str, pathlib.Path]:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise InputError(f"{label} must be a non-empty project-relative path")
    normalized = pathlib.PurePosixPath(value.replace("\\", "/")).as_posix()
    pure = pathlib.PurePosixPath(normalized)
    if pure.is_absolute() or ".." in pure.parts or normalized.startswith("//"):
        raise InputError(f"{label} must stay within the project root: {value}")
    if any(part.lower() in RESERVED_PATH_PARTS for part in pure.parts):
        raise InputError(f"{label} uses a reserved path: {value}")
    candidate = (root / pathlib.Path(*pure.parts)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise InputError(f"{label} escapes the project root: {value}") from exc
    if must_exist and not candidate.exists():
        raise InputError(f"{label} does not exist: {normalized}")
    return normalized, candidate


def extract_frontend_design(path: pathlib.Path) -> dict[str, Any]:
    text = decode_utf8(
        read_bytes(path, "frontend design artifact"),
        "frontend design artifact",
    ).replace("\r\n", "\n").replace("\r", "\n")
    if text.count(FRONTEND_START) != 1 or text.count(FRONTEND_END) != 1:
        raise InputError("frontend design artifact must contain exactly one managed design-system JSON block")
    start = text.index(FRONTEND_START) + len(FRONTEND_START)
    end = text.index(FRONTEND_END)
    if end <= start:
        raise InputError("frontend design managed block markers are out of order")
    match = re.fullmatch(r"\s*```json[ \t]*\n(?P<json>.*)\n[ \t]*```\s*", text[start:end], re.DOTALL)
    if not match:
        raise InputError("frontend design managed block must contain one fenced JSON object")
    try:
        value = json.loads(match.group("json"))
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid frontend design managed JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise InputError("frontend design managed JSON root must be an object")
    return value


def path_is_within(child: str, parent: str) -> bool:
    child_parts = pathlib.PurePosixPath(child).parts
    parent_parts = () if parent == "." else pathlib.PurePosixPath(parent).parts
    return child_parts[: len(parent_parts)] == parent_parts


def local_google_cli(project_root: pathlib.Path) -> tuple[str | None, pathlib.Path | None, str | None]:
    package = project_root / "node_modules" / "@google" / "design.md" / "package.json"
    version: str | None = None
    if package.is_file():
        try:
            value = json.loads(package.read_text(encoding="utf-8"))
            if isinstance(value, dict) and isinstance(value.get("version"), str):
                version = value["version"]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            version = None
    binary_names = ("designmd.cmd", "designmd") if sys.platform == "win32" else ("designmd",)
    binary = next((project_root / "node_modules" / ".bin" / name for name in binary_names if (project_root / "node_modules" / ".bin" / name).is_file()), None)
    npx = shutil.which("npx.cmd" if sys.platform == "win32" else "npx") or shutil.which("npx")
    return version, binary, npx


def run_official_crosscheck(
    project_root: pathlib.Path,
    design_path: pathlib.Path,
    profile: dict[str, Any],
) -> dict[str, Any]:
    expected = str(profile.get("upstream", {}).get("cli_version", ""))
    installed, binary, npx = local_google_cli(project_root)
    if installed is None and binary is None:
        return {"status": "NOT_INSTALLED", "required": False, "expected_version": expected}
    if installed != expected:
        return {
            "status": "VERSION_MISMATCH",
            "required": True,
            "expected_version": expected,
            "installed_version": installed,
        }
    if npx:
        argv = [npx, "--no-install", "designmd", "lint", "--format", "json", str(design_path)]
    elif binary:
        argv = [str(binary), "lint", "--format", "json", str(design_path)]
    else:
        return {
            "status": "UNAVAILABLE",
            "required": True,
            "expected_version": expected,
            "installed_version": installed,
        }
    try:
        completed = subprocess.run(
            argv,
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "ERROR",
            "required": True,
            "expected_version": expected,
            "installed_version": installed,
            "error": str(exc),
        }
    return {
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "required": True,
        "expected_version": expected,
        "installed_version": installed,
        "argv": ["npx", "--no-install", "designmd", "lint", "--format", "json", design_path.relative_to(project_root).as_posix()],
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def check_project(
    project_root: pathlib.Path,
    frontend_design: pathlib.Path,
    profile_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    root = project_root.resolve()
    try:
        frontend_design = frontend_design.resolve()
        frontend_design.relative_to(root)
    except ValueError as exc:
        raise InputError("frontend design artifact must stay within the project root") from exc
    managed = extract_frontend_design(frontend_design)
    errors: list[str] = []
    warnings: list[str] = []
    if managed.get("schema_version") != SCHEMA_VERSION:
        errors.append("frontend design managed schema_version must be 1")
    raw_systems = managed.get("design_systems")
    if not isinstance(raw_systems, list) or not raw_systems:
        errors.append("frontend design managed design_systems must be a non-empty array")
        raw_systems = []
    systems: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    claimed_roots: set[str] = set()
    root_mappings: list[tuple[str, int]] = []
    for index, raw in enumerate(raw_systems):
        label = f"design_systems[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{label} must be an object")
            continue
        try:
            design_rel, design_path = safe_relative_path(root, raw.get("path"), label=f"{label}.path", must_exist=True)
        except (InputError, TypeError) as exc:
            errors.append(str(exc))
            continue
        if pathlib.PurePosixPath(design_rel).name != "DESIGN.md":
            errors.append(f"{label}.path must end in DESIGN.md")
        if design_rel in seen_paths:
            errors.append(f"duplicate design system path: {design_rel}")
        seen_paths.add(design_rel)
        profile_id = raw.get("profile")
        if not isinstance(profile_id, str) or not profile_id:
            errors.append(f"{label}.profile must be a non-empty string")
            profile_id = DEFAULT_PROFILE
        roots = raw.get("frontend_roots")
        if not isinstance(roots, list) or not roots or any(not isinstance(item, str) for item in roots):
            errors.append(f"{label}.frontend_roots must be a non-empty string array")
            roots = []
        implementations = raw.get("implementation_paths")
        if not isinstance(implementations, list) or not implementations or any(not isinstance(item, str) for item in implementations):
            errors.append(f"{label}.implementation_paths must be a non-empty string array")
            implementations = []
        normalized_roots: list[str] = []
        design_parent = pathlib.PurePosixPath(design_rel).parent.as_posix()
        for raw_root in roots:
            try:
                root_rel, root_path = safe_relative_path(root, raw_root, label=f"{label}.frontend_roots", must_exist=True)
                if not root_path.is_dir():
                    errors.append(f"{label}.frontend_roots is not a directory: {root_rel}")
                if root_rel in claimed_roots:
                    errors.append(f"frontend root is assigned more than once: {root_rel}")
                if not path_is_within(root_rel, design_parent):
                    errors.append(f"{label}.path must be at or above frontend root {root_rel}")
                claimed_roots.add(root_rel)
                normalized_roots.append(root_rel)
                root_mappings.append((root_rel, len(systems)))
            except InputError as exc:
                errors.append(str(exc))
        normalized_impl: list[str] = []
        for raw_impl in implementations:
            try:
                impl_rel, impl_path = safe_relative_path(root, raw_impl, label=f"{label}.implementation_paths", must_exist=True)
                if not impl_path.is_file() and not impl_path.is_dir():
                    errors.append(f"{label}.implementation_paths is not a file or directory: {impl_rel}")
                if normalized_roots and not any(path_is_within(impl_rel, item) for item in normalized_roots):
                    errors.append(f"{label}.implementation_paths is outside its frontend roots: {impl_rel}")
                normalized_impl.append(impl_rel)
            except InputError as exc:
                errors.append(str(exc))
        try:
            lint_result = lint_path(design_path, profile_id, profile_path)
            profile, _ = load_profile(profile_id, profile_path)
            official = run_official_crosscheck(root, design_path, profile)
            if lint_result["status"] != "PASS":
                errors.append(f"{design_rel}: local DESIGN.md profile validation failed")
            if official.get("required") and official.get("status") != "PASS":
                errors.append(f"{design_rel}: installed official CLI cross-check did not pass ({official.get('status')})")
            lint = {
                "status": lint_result["status"],
                "file": design_rel,
                "sha256": lint_result["sha256"],
                "profile_contract_sha256": lint_result["profile_contract_sha256"],
                "summary": lint_result["summary"],
                "findings": [
                    item for item in lint_result["findings"] if item["severity"] != "info"
                ],
            }
        except InputError as exc:
            errors.append(str(exc))
            lint = {"status": "FAIL", "findings": [], "summary": {"error": 1, "warning": 0, "info": 0}}
            official = {"status": "NOT_RUN", "required": False}
        systems.append(
            {
                "path": design_rel,
                "profile": profile_id,
                "frontend_roots": normalized_roots,
                "implementation_paths": normalized_impl,
                "lint": lint,
                "official_crosscheck": official,
            }
        )

    resolutions: list[dict[str, str]] = []
    for system_index, system in enumerate(systems):
        for implementation in system["implementation_paths"]:
            candidates = [
                (root_rel, owner)
                for root_rel, owner in root_mappings
                if path_is_within(implementation, root_rel)
            ]
            if not candidates:
                errors.append(f"no DESIGN.md mapping applies to implementation path: {implementation}")
                continue
            depth = max(0 if item[0] == "." else len(pathlib.PurePosixPath(item[0]).parts) for item in candidates)
            nearest = [item for item in candidates if (0 if item[0] == "." else len(pathlib.PurePosixPath(item[0]).parts)) == depth]
            if len(nearest) != 1:
                errors.append(f"ambiguous nearest DESIGN.md mapping for implementation path: {implementation}")
                continue
            owner = nearest[0][1]
            if owner != system_index:
                errors.append(
                    f"{implementation} is claimed by {system['path']} but nearest mapping is {systems[owner]['path']}"
                )
            resolutions.append({"implementation_path": implementation, "design_system": systems[owner]["path"]})

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not errors else "FAIL",
        "project_root": str(root),
        "frontend_design": frontend_design.relative_to(root).as_posix(),
        "design_systems": systems,
        "resolutions": sorted(resolutions, key=lambda item: item["implementation_path"]),
        "errors": errors,
        "warnings": warnings,
    }


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return
    status = payload.get("status", "ERROR")
    print(f"[{status}] DESIGN.md {payload.get('file') or payload.get('frontend_design') or ''}".rstrip())
    for item in payload.get("findings", []):
        print(f"[{item['severity'].upper()}] {item['rule']} {item['path']}: {item['message']}")
    for message in payload.get("errors", []):
        print(f"[ERROR] {message}")
    for message in payload.get("warnings", []):
        print(f"[WARN] {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and review DESIGN.md files with an installed EZPowers profile")
    parser.add_argument("--profile-contract", type=pathlib.Path, default=None, help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    lint_parser = subparsers.add_parser("lint", help="Validate one DESIGN.md")
    lint_parser.add_argument("--file", required=True, type=pathlib.Path)
    lint_parser.add_argument("--profile", default=DEFAULT_PROFILE)
    lint_parser.add_argument("--json", action="store_true")

    diff_parser = subparsers.add_parser("diff", help="Review token and section changes")
    diff_parser.add_argument("--before", required=True, type=pathlib.Path)
    diff_parser.add_argument("--after", required=True, type=pathlib.Path)
    diff_parser.add_argument("--profile", default=DEFAULT_PROFILE)
    diff_parser.add_argument("--json", action="store_true")

    project_parser = subparsers.add_parser("check-project", help="Validate frontend DESIGN.md mappings")
    project_parser.add_argument("--project-root", type=pathlib.Path, default=pathlib.Path("."))
    project_parser.add_argument("--frontend-design", required=True, type=pathlib.Path)
    project_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "lint":
            payload = lint_path(args.file.resolve(), args.profile, args.profile_contract)
            emit(payload, args.json)
            return 0 if payload["status"] == "PASS" else 1
        if args.command == "diff":
            payload = diff_paths(args.before.resolve(), args.after.resolve(), args.profile, args.profile_contract)
            emit(payload, args.json)
            return 0 if payload["status"] == "PASS" else 1
        project_root = args.project_root.resolve()
        frontend_design = args.frontend_design
        if not frontend_design.is_absolute():
            frontend_design = project_root / frontend_design
        payload = check_project(project_root, frontend_design, args.profile_contract)
        emit(payload, args.json)
        return 0 if payload["status"] == "PASS" else 1
    except InputError as exc:
        payload = {"schema_version": SCHEMA_VERSION, "status": "ERROR", "error": str(exc)}
        if getattr(args, "json", False):
            print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        else:
            print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
