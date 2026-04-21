# GitHub Workflows

Reusable GitHub Actions workflows with a deliberately small dependency surface.

<!-- toc -->

* [Security posture](#security-posture)
* [Available workflows](#available-workflows)
* [Usage](#usage)
* [This Repo](#this-repo)
* [Example](#example)
* [Cleanup GHCR](#cleanup-ghcr)
  * [What it does](#what-it-does)
  * [Inputs](#inputs)
  * [Caller configuration](#caller-configuration)
  * [Retention choice](#retention-choice)

<!-- Regenerate with "pre-commit run -a markdown-toc" -->

<!-- tocstop -->

## Security posture

* Prefer direct CLI installation for tools such as `golangci-lint`,
  `actionlint`, `gosec`, and `govulncheck` instead of extra marketplace
  actions.
* Prefer GitHub-owned actions where an action is still the leanest option.
* Pin every external `uses:` reference to a full commit SHA rather than a
  moving tag.
* Keep repository-specific deploy and publish logic local so shared workflows
  do not need internal secrets, URLs, or infrastructure assumptions.

## Available workflows

* `action-lint.yaml`: dedicated GitHub Actions workflow linting
* `cleanup-ghcr.yaml`: prune untagged GHCR package versions older than a
  configurable retention window (see [Cleanup GHCR](#cleanup-ghcr))
* `go-lint.yaml`: `golangci-lint` and `gofmt`
* `go-unit-tests.yaml`: `go vet`, `go test`, optional coverage upload, and
  `go mod tidy` validation
* `go-security.yaml`: `gosec` and `govulncheck`
* `helm-lint.yaml`: `helm lint` for a chart path you supply
* `pre-commit.yaml`: reusable `pre-commit run` with optional Go, Node, and
  Helm setup for repo-specific hooks
* `semantic-release-preview.yaml`: computes whether the current `main` commit
  would release and what the next version would be, without publishing
* `semantic-release.yaml`: semantic versioning and GitHub release creation,
  using a repository-local `.releaserc.json` when present and a built-in
  default otherwise

## Usage

Reference a workflow from another repository with `uses`:

```yaml
jobs:
  go-lint:
    uses: kupecloud/github-workflows/.github/workflows/go-lint.yaml@<full-commit-sha>

  action-lint:
    uses: kupecloud/github-workflows/.github/workflows/action-lint.yaml@<full-commit-sha>
```

Keep shared workflows generic, and keep repository-specific orchestration in
the consuming repository.

Prefer a full commit SHA in consuming repositories so workflow refs stay immutable.

Use `pre-commit.yaml` as the baseline hygiene gate where a repository already
has a `.pre-commit-config.yaml`, then keep stack-specific jobs such as Go
tests, Go security, or Helm lint as separate jobs where they add signal.

`semantic-release.yaml` does not require every consuming repository to carry
its own `.releaserc.json`. If the file exists in the consuming repository,
the workflow uses it as-is. If it does not exist, the workflow writes a
built-in default config that releases from `main` and uses
`@semantic-release/commit-analyzer`,
`@semantic-release/release-notes-generator`, and
`@semantic-release/github`.

For Terraform repositories that need the computed semantic version during
`plan` and `apply`, use `semantic-release-preview.yaml` before deploy to
derive `new_release_published` and `new_release_version`, then run the real
`semantic-release.yaml` publish step after a successful deploy.

## This Repo

This repository follows the same pattern it encourages elsewhere:

* `validate.yaml` runs lightweight checks on pull requests
* `main.yaml` runs on `main`, re-validates, then runs semantic-release

That keeps pull request checks fast while still giving the shared workflows
repo its own versioned release flow.

## Example

A stripped back `main.yaml` in a Go repository can look like this:

```yaml
name: Main

on:
  push:
    branches:
      - main
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  go-lint:
    name: Go Lint
    uses: kupecloud/github-workflows/.github/workflows/go-lint.yaml@<full-commit-sha>

  action-lint:
    name: Action Lint
    uses: kupecloud/github-workflows/.github/workflows/action-lint.yaml@<full-commit-sha>

  unit-tests:
    name: Unit Tests
    needs:
      - go-lint
      - action-lint
    uses: kupecloud/github-workflows/.github/workflows/go-unit-tests.yaml@<full-commit-sha>

  gosec:
    name: Go Security
    needs:
      - unit-tests
    uses: kupecloud/github-workflows/.github/workflows/go-security.yaml@<full-commit-sha>

  release:
    name: Release
    needs:
      - gosec
    uses: kupecloud/github-workflows/.github/workflows/semantic-release.yaml@<full-commit-sha>
    permissions:
      contents: write
      issues: write
      pull-requests: write
    secrets: inherit
```

If a repository also has custom build or publish steps, keep those as local
workflows and call them from the local `main.yaml` after the shared lint,
test, security, and release jobs.

## Cleanup GHCR

Container registry tags are mutable pointers; each push of a reused tag
(`:dev`, `:main`, a rebuilt `:vX.Y.Z`) leaves the previous manifest behind
as an untagged version. Those orphans accumulate forever unless something
deletes them. `cleanup-ghcr.yaml` does the deletion.

### What it does

For a single GHCR package:

* Lists every version via the GitHub API.
* Keeps every **tagged** version — pruning those is the caller's call,
  not this workflow's.
* Keeps every **untagged** version whose `updated_at` is within the
  retention window.
* Deletes everything else.

Every run writes a job summary with the counts (kept tagged, kept recent,
deleted).

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `package_name` | string | repository name | GHCR package name under the owner. Override when it does not match the repo. |
| `retention_days` | number | `7` | Delete untagged versions older than this many days. |
| `owner_type` | string | `orgs` | Either `orgs` or `users`. Org-owned packages use `orgs`; user-owned use `users`. |
| `dry_run` | boolean | `false` | When `true`, log candidates without deleting. |

### Caller configuration

Callers schedule the cleanup themselves and declare `packages: write` at
the job level so the reusable workflow's `GITHUB_TOKEN` can delete
versions. Weekly on Mondays at 03:00 UTC is a reasonable default — tune
per repository if your dev push cadence is higher:

```yaml
name: Cleanup GHCR

on:
  schedule:
    - cron: "0 3 * * 1"
  workflow_dispatch:
    inputs:
      retention_days:
        description: Keep untagged versions updated within this many days.
        required: false
        type: number
        default: 7
      dry_run:
        description: Log candidates without deleting anything.
        required: false
        type: boolean
        default: false

permissions:
  contents: read

jobs:
  cleanup:
    name: Cleanup GHCR untagged versions
    uses: kupecloud/github-workflows/.github/workflows/cleanup-ghcr.yaml@<full-commit-sha>
    permissions:
      packages: write
    with:
      retention_days: ${{ inputs.retention_days || 7 }}
      dry_run: ${{ inputs.dry_run || false }}
```

For repositories that push multiple GHCR packages, duplicate the job and
pass `package_name:` per call.

### Retention choice

The default (7 days) is aimed at services that push a reused tag many
times per day during active development. It keeps enough history to
roll back recent `:dev` or `:main` pushes while still pruning aggressively.
Pass a larger value for repositories where the reused tag changes only
during a release window.
