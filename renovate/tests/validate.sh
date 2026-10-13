#!/usr/bin/env bash
# Validate the org-wide Renovate preset:
#   1. renovate-config-validator — schema/option validation
#   2. check_regex_fixtures.py   — custom managers' managerFilePatterns +
#      matchString against fixtures: the argocd prod-pin manager on a realistic
#      values/prod.yaml, and the workflow input-default manager on a fixture
#      workflow plus this repo's own .github/workflows
#
# Run locally before pushing changes to renovate/default.json; CI runs it on
# every PR. This preset is consumed by EVERY kupecloud repo, so a bad merge here
# breaks dependency management org-wide.
set -euo pipefail
cd "$(dirname "$0")/.."

# --strict fails the gate on warnings too (e.g. "Config migration necessary"),
# so a re-introduced deprecated option key can't silently merge org-wide.
npx --yes --package renovate -- renovate-config-validator --strict default.json

python3 tests/check_regex_fixtures.py
