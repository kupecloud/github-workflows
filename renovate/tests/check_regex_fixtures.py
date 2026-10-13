#!/usr/bin/env python3
"""Fixture tests for custom managers in renovate/default.json.

Reads the managerFilePatterns regex and matchString straight from default.json
(no duplicated regex to drift).

argocd prod-pin manager, against tests/fixtures/values/prod.yaml:

  1. managerFilePatterns matches the file where it actually lives in
     kupecloud/argocd (values/prod.yaml at repo root) and not dev values files.
  2. matchString extracts exactly the real (uncommented) entries — a
     commented-out example repoURL must never cross-bind to a real
     gitRevision line (review-fable-2 HIGH-1/HIGH-2 regressions).

workflow input-default manager, against tests/fixtures/workflows/tool-versions.yaml
and this repo's own .github/workflows:

  3. managerFilePatterns matches workflow files at the repo root only.
  4. matchString extracts helm/helm v4.3.0 from a marked `default:` and does
     not match an unmarked default or a marker that is not directly above one.
  5. Every reusable workflow with a helm-version input is tracked, and nothing
     but helm/helm is: the yq/prometheus/lokitool versions are paired with a
     sha256 input that a version-only Renovate bump would leave stale.

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


def manager_regexes(manager: dict) -> tuple[str, str]:
    """Return (file_match, match_string) as Python regexes.

    managerFilePatterns entries are Renovate `/regex/` values (post config
    migration). Strip the delimiters to recover the raw regex, which carries
    the same semantics as the pre-migration fileMatch.
    """
    pattern = manager["managerFilePatterns"][0]
    file_match = (
        pattern[1:-1] if pattern.startswith("/") and pattern.endswith("/") else pattern
    )
    return file_match, manager["matchStrings"][0].replace("(?<", "(?P<")


manager = next(
    m
    for m in config["customManagers"]
    if m.get("datasourceTemplate") == "github-releases"
)
file_match, match_string = manager_regexes(manager)

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

# --- 3-5. workflow input-default manager ---
WORKFLOWS_DIR = REPO_ROOT.parent / ".github" / "workflows"
WORKFLOW_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "workflows" / "tool-versions.yaml"
HELM_WORKFLOWS = (
    "helm-lint.yaml",
    "helm-rbac-audit.yaml",
    "helm-automount-audit.yaml",
    "promtool-rules.yaml",
)

workflow_manager = next(
    m
    for m in config["customManagers"]
    if any(".github/workflows" in p for p in m["managerFilePatterns"])
)
wf_file_match, wf_match_string = manager_regexes(workflow_manager)


def extract_defaults(text: str) -> list[tuple[str, str]]:
    return [
        (m.group("depName"), m.group("currentValue"))
        for m in re.finditer(wf_match_string, text)
    ]


for target in (".github/workflows/helm-lint.yaml", ".github/workflows/ci.yml"):
    check(
        f"workflow managerFilePatterns matches {target}",
        re.search(wf_file_match, target) is not None,
        wf_file_match,
    )
for non_target in (
    "values.yaml",
    ".github/workflows/sub/x.yaml",
    "foo/.github/workflows/x.yaml",
    ".github/actions/tofu/action.yaml",
):
    check(
        f"workflow managerFilePatterns does NOT match {non_target}",
        re.search(wf_file_match, non_target) is None,
        wf_file_match,
    )

wf_extracted = extract_defaults(WORKFLOW_FIXTURE.read_text())
check(
    "workflow matchString extracts exactly helm/helm v4.3.0 from the fixture",
    wf_extracted == [("helm/helm", "v4.3.0")],
    f"got {wf_extracted!r}",
)
check(
    "unmarked yq-version default does not match",
    all(value != "v4.52.5" for _, value in wf_extracted),
    f"got {wf_extracted!r}",
)
check(
    "marker not directly above a default does not bind",
    all(dep != "grafana/loki" for dep, _ in wf_extracted),
    f"got {wf_extracted!r}",
)

for workflow in sorted(WORKFLOWS_DIR.glob("*.y*ml")):
    found = extract_defaults(workflow.read_text())
    if workflow.name in HELM_WORKFLOWS:
        check(
            f"{workflow.name} helm-version default is tracked",
            [dep for dep, _ in found] == ["helm/helm"],
            f"got {found!r}",
        )
    else:
        check(
            f"{workflow.name} has no marked default",
            found == [],
            f"got {found!r}",
        )

if failures:
    print(f"\n{len(failures)} fixture assertion(s) failed", file=sys.stderr)
    sys.exit(1)
print("\nall fixture assertions passed")
