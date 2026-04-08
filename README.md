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

* `go-lint.yaml`: `golangci-lint`, `gofmt`, and `actionlint`
* `go-unit-tests.yaml`: `go vet`, `go test`, optional coverage upload, and
  `go mod tidy` validation
* `go-security.yaml`: `gosec` and `govulncheck`
* `helm-lint.yaml`: `helm lint` for a chart path you supply
* `semantic-release.yaml`: semantic versioning and GitHub release creation

## Usage

Reference a workflow from another repository with `uses`:

```yaml
jobs:
  lint:
    uses: kupecloud/github-workflows/.github/workflows/go-lint.yaml@09fcdad22d0195c319ead621bb5320da422ee4ac
```

Keep shared workflows generic, and keep repository-specific orchestration in
the consuming repository.

Prefer a full commit SHA in consuming repositories so workflow refs stay immutable.

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
  lint:
    name: Lint
    uses: kupecloud/github-workflows/.github/workflows/go-lint.yaml@09fcdad22d0195c319ead621bb5320da422ee4ac

  unit-tests:
    name: Unit Tests
    uses: kupecloud/github-workflows/.github/workflows/go-unit-tests.yaml@09fcdad22d0195c319ead621bb5320da422ee4ac

  gosec:
    name: Go Security
    needs:
      - lint
      - unit-tests
    uses: kupecloud/github-workflows/.github/workflows/go-security.yaml@09fcdad22d0195c319ead621bb5320da422ee4ac

  release:
    name: Release
    needs:
      - gosec
    uses: kupecloud/github-workflows/.github/workflows/semantic-release.yaml@09fcdad22d0195c319ead621bb5320da422ee4ac
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
