#!/usr/bin/env python3
"""Fixture tests for the argocd prod-pin custom manager in renovate/default.json.

Reads the managerFilePatterns regex and matchString straight from default.json
(no duplicated regex to drift) and asserts against tests/fixtures/values/prod.yaml:

  1. managerFilePatterns matches the file where it actually lives in
     kupecloud/argocd (values/prod.yaml at repo root) and not dev values files.
  2. matchString extracts exactly the real (uncommented) entries — a
     commented-out example repoURL must never cross-bind to a real
     gitRevision line (review-fable-2 HIGH-1/HIGH-2 regressions).

Renovate compiles matchStrings with RE2; the syntax used here ((?sm), ^, \\s,
character classes, lazy .*?) is common to RE2 and Python re. Python requires
(?P<name>) for named groups where RE2 accepts (?<name>), so that spelling is
translated before compiling.
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "values" / "prod.yaml"

EXPECTED = [
    ("cert-manager", "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678", "v1.2.3"),
    ("crds", "0" * 40, "v0.0.0"),
]
MUST_NOT_BIND = {"openbao", "external-dns"}

failures = []


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "ok" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


config = json.loads((REPO_ROOT / "default.json").read_text())
manager = next(
    m
    for m in config["customManagers"]
    if m.get("datasourceTemplate") == "github-releases"
)
# managerFilePatterns entries are Renovate `/regex/` values (post config
# migration). Strip the delimiters to recover the raw regex, which carries the
# same semantics as the pre-migration fileMatch.
_pattern = manager["managerFilePatterns"][0]
file_match = (
    _pattern[1:-1]
    if _pattern.startswith("/") and _pattern.endswith("/")
    else _pattern
)
match_string = manager["matchStrings"][0].replace("(?<", "(?P<")

# --- 1. managerFilePatterns behaves like Renovate's (regex over repo-relative path) ---
check(
    "managerFilePatterns matches values/prod.yaml at repo root",
    re.search(file_match, "values/prod.yaml") is not None,
    file_match,
)
check(
    "managerFilePatterns matches nested */values/prod.yaml",
    re.search(file_match, "charts/foo/values/prod.yaml") is not None,
    file_match,
)
for non_target in ("values/dev.yaml", "values.yaml", "docs/values/prod.yaml.md"):
    check(
        f"managerFilePatterns does NOT match {non_target}",
        re.search(file_match, non_target) is None,
        file_match,
    )

# --- 2. matchString extraction against the fixture ---
content = FIXTURE.read_text()
extracted = [
    (m.group("packageName"), m.group("currentDigest"), m.group("currentValue"))
    for m in re.finditer(match_string, content)
]

check(
    "matchString extracts exactly the real entries",
    extracted == EXPECTED,
    f"got {extracted!r}, want {EXPECTED!r}",
)
bound_packages = {pkg for pkg, _, _ in extracted}
for pkg in sorted(MUST_NOT_BIND):
    check(
        f"commented-out {pkg} example does not bind to a real gitRevision",
        pkg not in bound_packages,
        f"{pkg} cross-bound: {extracted!r}",
    )

if failures:
    print(f"\n{len(failures)} fixture assertion(s) failed", file=sys.stderr)
    sys.exit(1)
print("\nall fixture assertions passed")
