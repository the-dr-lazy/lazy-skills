#!/usr/bin/env python3
"""Validate the structure of every skill in skills/ and the plugin manifests.

Checks, per skill directory:
  - SKILL.md exists and starts with a YAML frontmatter block
  - frontmatter keys are known; `name` and `description` are present
  - `name` is 1-64 chars of [a-z0-9-] (no leading, trailing, or doubled
    hyphens) and equals the directory name
  - `description` is 1-1024 chars and contains no XML tags
  - SKILL.md stays under MAX_LINES lines
  - code fences are balanced in every .md file
  - relative Markdown links resolve to existing files
Repository-wide:
  - .claude-plugin/plugin.json and marketplace.json parse and carry `name`
  - README.md links every skill

Usage: tools/check_skills.py [skill dirs...]   (default: all of skills/*)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^\s*(```|~~~)")
MAX_LINES = 500


def frontmatter(text: str) -> tuple[dict | None, str]:
    if not text.startswith("---\n"):
        return None, "missing frontmatter (file must start with '---')"
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, "unterminated frontmatter"
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError as e:
        return None, f"invalid YAML frontmatter: {e}"
    if not isinstance(data, dict):
        return None, "frontmatter is not a mapping"
    return data, ""


def check_markdown(path: Path) -> list[str]:
    errors, open_fence = [], None
    lines = path.read_text(encoding="utf-8").splitlines()
    for no, line in enumerate(lines, 1):
        m = FENCE.match(line)
        if m:
            open_fence = None if open_fence else no
            continue
        if open_fence:
            continue
        for target in LINK.findall(line):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            file = target.split("#", 1)[0]
            if file and not (path.parent / file).exists():
                errors.append(f"{path.relative_to(ROOT)}:{no}: broken link to {target}")
    if open_fence:
        errors.append(f"{path.relative_to(ROOT)}:{open_fence}: unclosed code fence")
    return errors


def check_skill(d: Path) -> list[str]:
    rel = d.relative_to(ROOT)
    skill_md = d / "SKILL.md"
    if not skill_md.is_file():
        return [f"{rel}: missing SKILL.md"]
    text = skill_md.read_text(encoding="utf-8")
    data, err = frontmatter(text)
    if data is None:
        return [f"{rel}/SKILL.md: {err}"]
    errors = []
    if unknown := sorted(set(data) - ALLOWED_KEYS):
        errors.append(f"{rel}/SKILL.md: unknown frontmatter keys {unknown}")
    name, desc = data.get("name"), data.get("description")
    if not isinstance(name, str) or not NAME.match(name) or len(name) > 64:
        errors.append(f"{rel}/SKILL.md: name {name!r} must be 1-64 chars of lowercase letters, digits, single hyphens")
    elif name != d.name:
        errors.append(f"{rel}/SKILL.md: name {name!r} does not match directory {d.name!r}")
    if not isinstance(desc, str) or not desc.strip():
        errors.append(f"{rel}/SKILL.md: description is missing or empty")
    else:
        if len(desc) > 1024:
            errors.append(f"{rel}/SKILL.md: description is {len(desc)} chars (max 1024)")
        if re.search(r"<[^>]+>", desc):
            errors.append(f"{rel}/SKILL.md: description must not contain XML tags")
    if (n := text.count("\n") + 1) > MAX_LINES:
        errors.append(f"{rel}/SKILL.md: {n} lines (keep under {MAX_LINES}; move detail to reference files)")
    for md in sorted(d.rglob("*.md")):
        errors += check_markdown(md)
    return errors


def check_repo(skill_dirs: list[Path]) -> list[str]:
    errors = []
    for manifest in ("plugin.json", "marketplace.json"):
        p = ROOT / ".claude-plugin" / manifest
        try:
            if not json.loads(p.read_text()).get("name"):
                errors.append(f"{p.relative_to(ROOT)}: missing 'name'")
        except (OSError, json.JSONDecodeError) as e:
            errors.append(f"{p.relative_to(ROOT)}: {e}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for d in skill_dirs:
        if f"skills/{d.name}/SKILL.md" not in readme:
            errors.append(f"README.md: skill {d.name!r} is not linked")
    errors += check_markdown(ROOT / "README.md")
    return errors


def main(argv: list[str]) -> int:
    all_dirs = sorted(p for p in SKILLS.iterdir() if p.is_dir())
    dirs = sorted({(ROOT / a).resolve() for a in argv}) if argv else all_dirs
    errors = [e for d in dirs for e in check_skill(d)]
    errors += check_repo(all_dirs)
    for e in errors:
        print(e)
    print(f"{len(dirs)} skills checked, {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
