#!/usr/bin/env python3
"""Resolve EZPowers model profiles into backend-specific model selections.

The router is intentionally deterministic and file-based. It does not contact
providers; it reads .harness/config.json plus an optional availability cache.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


BACKEND_ALIASES = {
    "claude": "claude-code",
    "claude_code": "claude-code",
    "claude-code": "claude-code",
    "codex": "codex-cli",
    "codex_cli": "codex-cli",
    "codex-cli": "codex-cli",
    "harness": "harness-env",
    "harness_env": "harness-env",
    "harness-env": "harness-env",
}

DEFAULT_PROFILES: dict[str, dict[str, list[dict[str, Any]]]] = {
    "quick-fix": {
        "claude-code": [{"model": "haiku"}, {"model": "sonnet"}],
        "codex-cli": [{"model": "gpt-5.3-codex-spark"}, {"model": "gpt-5.4"}],
        "harness-env": [{"model": "claude-haiku-4-5"}, {"model": "gpt-5.4-mini"}],
    },
    "balanced": {
        "claude-code": [{"model": "sonnet"}, {"model": "opus"}],
        "codex-cli": [{"model": "gpt-5.5"}, {"model": "gpt-5.4"}],
        "harness-env": [{"model": "claude-sonnet-5"}, {"model": "gpt-5.5"}],
    },
    "deep-analysis": {
        "claude-code": [{"model": "opus"}, {"model": "sonnet"}],
        "codex-cli": [{"model": "gpt-5.5-pro"}, {"model": "gpt-5.5"}],
        "harness-env": [
            {"model": "claude-opus-4-8", "variant": "max"},
            {"model": "gpt-5.5", "reasoning_effort": "high"},
        ],
    },
    "contract-review": {
        "claude-code": [{"model": "opus"}, {"model": "sonnet"}],
        "codex-cli": [{"model": "gpt-5.5"}, {"model": "gpt-5.4"}],
        "harness-env": [
            {"model": "claude-opus-4-8", "variant": "max"},
            {"model": "gpt-5.5", "reasoning_effort": "high"},
        ],
    },
    "runtime-debug": {
        "claude-code": [{"model": "sonnet"}, {"model": "opus"}],
        "codex-cli": [{"model": "gpt-5.5"}, {"model": "gpt-5.4"}],
        "harness-env": [{"model": "claude-sonnet-5"}, {"model": "gpt-5.5"}],
    },
    "frontend-visual": {
        "claude-code": [{"model": "opus"}, {"model": "sonnet"}],
        "codex-cli": [{"model": "gpt-5.5"}, {"model": "gpt-5.4"}],
        "harness-env": [
            {"model": "gemini-3.1-pro", "reasoning_effort": "high"},
            {"model": "claude-opus-4-8", "variant": "max"},
        ],
    },
    "security-audit": {
        "claude-code": [{"model": "opus"}, {"model": "sonnet"}],
        "codex-cli": [{"model": "gpt-5.5-pro"}, {"model": "gpt-5.5"}],
        "harness-env": [
            {"model": "claude-opus-4-8", "variant": "max"},
            {"model": "gpt-5.5", "reasoning_effort": "high"},
        ],
    },
    "docs-sync": {
        "claude-code": [{"model": "sonnet"}, {"model": "haiku"}],
        "codex-cli": [{"model": "gpt-5.4"}, {"model": "gpt-5.3-codex-spark"}],
        "harness-env": [{"model": "claude-sonnet-5"}, {"model": "gpt-5.4-mini"}],
    },
}


def load_json(path: pathlib.Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def normalize_backend(value: str) -> str:
    key = value.strip().lower().replace("_", "-")
    return BACKEND_ALIASES.get(key, key)


def normalize_entry(entry: Any) -> dict[str, Any] | None:
    if isinstance(entry, str):
        model = entry.strip()
        return {"model": model} if model else None
    if isinstance(entry, dict):
        model = str(entry.get("model", "")).strip()
        if not model:
            return None
        normalized = {"model": model}
        for key in ("variant", "reasoning_effort", "temperature", "top_p", "maxTokens"):
            if key in entry and entry[key] not in ("", None):
                normalized[key] = entry[key]
        return normalized
    return None


def normalize_profile_config(raw: Any) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(raw, dict):
        return result

    for raw_backend, values in raw.items():
        backend = normalize_backend(str(raw_backend))
        if backend in {"description", "disable"}:
            continue
        if isinstance(values, (str, dict)):
            values = [values]
        if not isinstance(values, list):
            continue
        entries = [entry for item in values if (entry := normalize_entry(item))]
        if entries:
            result[backend] = entries
    return result


def merge_profiles(config_profiles: Any) -> dict[str, dict[str, list[dict[str, Any]]]]:
    profiles = {
        name: {backend: [dict(entry) for entry in entries] for backend, entries in backends.items()}
        for name, backends in DEFAULT_PROFILES.items()
    }
    if not isinstance(config_profiles, dict):
        return profiles

    for name, raw_profile in config_profiles.items():
        normalized = normalize_profile_config(raw_profile)
        if not normalized:
            continue
        current = profiles.setdefault(str(name), {})
        current.update(normalized)
    return profiles


def read_availability(project_root: pathlib.Path, cache_value: Any) -> dict[str, set[str]] | None:
    cache_path = pathlib.Path(str(cache_value or ".harness/model-availability.json"))
    if not cache_path.is_absolute():
        cache_path = project_root / cache_path
    if not cache_path.exists():
        return None

    data = load_json(cache_path)
    raw_models = data.get("models", data) if isinstance(data, dict) else data
    if not isinstance(raw_models, dict):
        return {}

    result: dict[str, set[str]] = {}
    for raw_backend, values in raw_models.items():
        backend = normalize_backend(str(raw_backend))
        items: list[str] = []
        if isinstance(values, list):
            for item in values:
                if isinstance(item, str):
                    items.append(item)
                elif isinstance(item, dict) and item.get("model"):
                    items.append(str(item["model"]))
        elif isinstance(values, dict):
            for key, value in values.items():
                if value is True or isinstance(value, (dict, list, str)):
                    items.append(str(key))
        result[backend] = {item.lower() for item in items if item.strip()}
    return result


def model_available(entry: dict[str, Any], available: set[str]) -> bool:
    model = str(entry["model"]).lower()
    return model in available or any(model in candidate or candidate in model for candidate in available)


def resolve(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    project_root = pathlib.Path(args.project_root).resolve()
    config_path = project_root / ".harness" / "config.json"
    config: dict[str, Any] = {}
    if config_path.exists():
        loaded = load_json(config_path)
        if isinstance(loaded, dict):
            config = loaded

    executor = config.get("executor", {}) if isinstance(config.get("executor"), dict) else {}
    routing = executor.get("model_routing", {}) if isinstance(executor.get("model_routing"), dict) else {}
    enabled = bool(routing.get("enabled", False))
    backend = normalize_backend(args.backend)
    default_profile = str(routing.get("default_profile", "balanced") or "balanced")
    profile = args.profile or default_profile
    fail_on_unresolved = bool(routing.get("fail_on_unresolved", False))

    result: dict[str, Any] = {
        "enabled": enabled,
        "profile": profile,
        "backend": backend,
        "selected": None,
        "variant": None,
        "reasoning_effort": None,
        "provenance": "disabled",
        "attempted": [],
        "status": "disabled",
        "reason": "model_routing.enabled is false or absent",
    }

    explicit_model = args.explicit_model.strip() if args.explicit_model else ""
    if explicit_model:
        result.update(
            {
                "enabled": enabled,
                "selected": explicit_model,
                "provenance": "explicit-override",
                "status": "resolved",
                "reason": "explicit model override",
            }
        )
        return result, 0

    if not enabled:
        return result, 0

    legacy_override = ""
    if backend == "claude-code":
        legacy_override = str(executor.get("reviewer_model", "") or "").strip()
    elif backend == "codex-cli":
        legacy_override = str(executor.get("codex_reviewer_model", "") or "").strip()
    if legacy_override:
        result.update(
            {
                "selected": legacy_override,
                "provenance": "legacy-override",
                "status": "resolved",
                "reason": "legacy reviewer model override",
            }
        )
        return result, 0

    profiles = merge_profiles(routing.get("profiles"))
    profile_config = profiles.get(profile)
    if not profile_config:
        result.update(
            {
                "provenance": "profile-fallback",
                "status": "unresolved",
                "reason": f"unknown profile: {profile}",
            }
        )
        return result, 1 if fail_on_unresolved else 0

    fallback = profile_config.get(backend) or profile_config.get("default") or []
    result["attempted"] = [entry["model"] for entry in fallback]
    if not fallback:
        result.update(
            {
                "provenance": "profile-fallback",
                "status": "unresolved",
                "reason": f"profile {profile} has no fallback for backend {backend}",
            }
        )
        return result, 1 if fail_on_unresolved else 0

    availability = read_availability(project_root, routing.get("availability_cache"))
    selected = fallback[0]
    if availability is None:
        status = "unverified"
        reason = "availability cache missing; selected first fallback"
    else:
        available = availability.get(backend, set())
        selected = next((entry for entry in fallback if model_available(entry, available)), {})
        if not selected:
            result.update(
                {
                    "provenance": "profile-fallback",
                    "status": "unresolved",
                    "reason": f"no fallback model for {profile}/{backend} is available",
                }
            )
            return result, 1 if fail_on_unresolved else 0
        status = "resolved"
        reason = "selected from availability cache"

    result.update(
        {
            "selected": selected.get("model"),
            "variant": selected.get("variant"),
            "reasoning_effort": selected.get("reasoning_effort"),
            "temperature": selected.get("temperature"),
            "top_p": selected.get("top_p"),
            "maxTokens": selected.get("maxTokens"),
            "provenance": "profile-fallback",
            "status": status,
            "reason": reason,
        }
    )
    return result, 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve an EZPowers model profile")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--backend", required=True)
    parser.add_argument("--profile", default="")
    parser.add_argument("--explicit-model", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result, code = resolve(args)
    except Exception as exc:  # noqa: BLE001 - CLI must report structured failure
        result = {
            "enabled": False,
            "profile": args.profile,
            "backend": normalize_backend(args.backend),
            "selected": None,
            "provenance": "error",
            "attempted": [],
            "status": "error",
            "reason": str(exc),
        }
        code = 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['status']}: {result.get('selected') or '-'} ({result['reason']})")
    return code


if __name__ == "__main__":
    sys.exit(main())
