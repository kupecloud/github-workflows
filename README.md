# GitHub Workflows

Reusable GitHub Actions workflows with a deliberately small dependency surface.

<!-- toc -->

* [Security posture](#security-posture)
* [Available workflows](#available-workflows)
* [Usage](#usage)
* [This Repo](#this-repo)
* [Example](#example)

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
* `go-lint.yaml`: `golangci-lint` and `gofmt`
* `go-unit-tests.yaml`: `go vet`, `go test`, optional coverage upload, and
  `go mod tidy` validation
* `go-security.yaml`: `gosec` and `govulncheck`
* `helm-lint.yaml`: `helm lint` for a chart path you supply
* `pre-commit.yaml`: reusable `pre-commit run` with optional Go, Node, and
  Helm setup for repo-specific hooks
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
      packages: write
      id-token: write
    secrets: inherit
```

If a repository also has custom build or publish steps, keep those as local
workflows and call them from the local `main.yaml` after the shared lint,
test, security, and release jobs.
