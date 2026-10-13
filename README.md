# GitHub Workflows

Reusable GitHub Actions workflows with a deliberately small dependency surface.

<!-- toc -->

* [Security posture](#security-posture)
* [Available workflows](#available-workflows)
* [Usage](#usage)
  * [Digest-pinned image releases](#digest-pinned-image-releases)
* [This Repo](#this-repo)
* [Example](#example)
* [Action Lint](#action-lint)
  * [Inputs](#inputs)
* [Cleanup GHCR](#cleanup-ghcr)
  * [What it does](#what-it-does)
  * [Inputs](#inputs-1)
  * [Caller configuration](#caller-configuration)
  * [Retention choice](#retention-choice)
* [Detect Changes](#detect-changes)
  * [Inputs](#inputs-2)
  * [Outputs](#outputs)
* [Go Lint](#go-lint)
  * [Inputs](#inputs-3)
* [Go Security](#go-security)
  * [Inputs](#inputs-4)
* [Go Unit Tests](#go-unit-tests)
  * [Inputs](#inputs-5)
* [Helm Automount Audit](#helm-automount-audit)
  * [Inputs](#inputs-6)
* [Helm Lint](#helm-lint)
  * [Inputs](#inputs-7)
* [Helm RBAC Audit](#helm-rbac-audit)
  * [Inputs](#inputs-8)
* [Node Build](#node-build)
  * [Inputs](#inputs-9)
* [Node Lint](#node-lint)
  * [Inputs](#inputs-10)
* [Node Security](#node-security)
  * [Inputs](#inputs-11)
* [Node Unit Tests](#node-unit-tests)
  * [Inputs](#inputs-12)
* [Packer Build](#packer-build)
  * [Inputs](#inputs-13)
  * [Secrets](#secrets)
* [Packer Test](#packer-test)
  * [Inputs](#inputs-14)
  * [Secrets](#secrets-1)
* [Packer Validate](#packer-validate)
  * [Inputs](#inputs-15)
* [Pre-Commit](#pre-commit)
  * [Inputs](#inputs-16)
* [Promtool Rules](#promtool-rules)
  * [Inputs](#inputs-17)
* [Publish Image](#publish-image)
  * [Inputs](#inputs-18)
  * [Outputs](#outputs-1)
* [Publish Node Image](#publish-node-image)
  * [Inputs](#inputs-19)
  * [Outputs](#outputs-2)
* [Semantic Release Preview](#semantic-release-preview)
  * [Inputs](#inputs-20)
  * [Outputs](#outputs-3)
* [Semantic Release](#semantic-release)
  * [Inputs](#inputs-21)
  * [Outputs](#outputs-4)

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
* Check every downloaded binary or archive against the SHA-256 its upstream
  release publishes, in a `mktemp -d -p "$RUNNER_TEMP"` directory, before it
  is unpacked or run. Version and checksum are paired inputs with defaults, so
  a bump changes both together. A tool installed by a SHA-pinned setup action,
  or by `go install` at a pinned version (checked against the Go checksum
  database), needs no extra step.
* Pass inputs to `run:` steps through `env:`, never as `${{ inputs.* }}`
  inside the script. Inputs that are shell words by contract (`*-args`,
  `*-command`) are parsed from that variable with `eval`, so callers keep the
  quoting and `$VAR` expansion they always had.
* Start every multi-line `run:` with `set -euo pipefail`.

## Available workflows

* [`action-lint.yaml`](#action-lint): dedicated GitHub Actions workflow linting
* [`cleanup-ghcr.yaml`](#cleanup-ghcr): prune untagged GHCR package versions
  older than a configurable retention window
* [`detect-changes.yaml`](#detect-changes): whether any listed path changed
  between the event's base and head commits
* [`go-lint.yaml`](#go-lint): `golangci-lint`, `gofmt`, and a Dockerfile builder
  vs `go.mod` drift check
* [`go-security.yaml`](#go-security): `gosec` and `govulncheck`
* [`go-unit-tests.yaml`](#go-unit-tests): `go vet`, `go test`, optional coverage
  upload, and `go mod tidy` validation
* [`helm-automount-audit.yaml`](#helm-automount-audit): lists workloads in a
  rendered chart that mount a service account token
* [`helm-lint.yaml`](#helm-lint): `helm lint` for a chart path you supply
* [`helm-rbac-audit.yaml`](#helm-rbac-audit): fails when a rendered ClusterRole
  can read `secrets` cluster-wide
* [`node-build.yaml`](#node-build): `npm ci` and an npm build script, with
  optional artifact upload
* [`node-lint.yaml`](#node-lint): npm lint and TypeScript check scripts
* [`node-security.yaml`](#node-security): `npm audit` against
  `package-lock.json`
* [`node-unit-tests.yaml`](#node-unit-tests): an npm test script, with optional
  coverage upload
* [`packer-build.yaml`](#packer-build): `packer init`, `validate` and `build`
* [`packer-test.yaml`](#packer-test): the repository's Packer image smoke test
* [`packer-validate.yaml`](#packer-validate): `packer init`, `fmt -check` and
  `validate`
* [`pre-commit.yaml`](#pre-commit): reusable `pre-commit run` with optional Go,
  Node, and Helm setup for repo-specific hooks
* [`promtool-rules.yaml`](#promtool-rules): checksum-verified yq and promtool,
  then the caller's alert rule test script; with `loki-rules-script` set, also
  checksum-verified lokitool and the caller's LogQL lint script
* [`publish-image.yaml`](#publish-image): build, push and cosign-sign a
  multi-platform image to GHCR, and output its digest
* [`publish-node-image.yaml`](#publish-node-image): `publish-image.yaml` with an
  `npm ci` and npm build first
* [`semantic-release-preview.yaml`](#semantic-release-preview): computes whether
  the current `main` commit would release and what the next version would be,
  without publishing
* [`semantic-release.yaml`](#semantic-release): semantic versioning and GitHub
  release creation, using a repository-local `.releaserc.json` when present and
  a built-in default otherwise

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

### Digest-pinned image releases

To make the release commit (the one the git tag points at) pin the image by
digest, build before releasing:

1. `semantic-release-preview.yaml` computes the next version.
2. `publish-image.yaml` builds, pushes and signs that version and outputs
   `digest`.
3. `semantic-release.yaml` runs with `image-digest` and `image-version`, which
   reach semantic-release as `$IMAGE_DIGEST` / `$IMAGE_VERSION`. The repo's
   `@semantic-release/exec` prepareCmd guards and stamps, e.g.

   ```sh
   test -n "$IMAGE_DIGEST" && test "$IMAGE_VERSION" = "${nextRelease.version}" && sed -i -E '... tag: "v${nextRelease.version}@'"$IMAGE_DIGEST"'"|' chart/values/prod.yaml
   ```

   Write `$IMAGE_DIGEST` without braces, because `${...}` is lodash template
   syntax. Close the single quotes around it, or the shell never expands it
   and the chart is stamped with the literal text `$IMAGE_DIGEST`.

A release that fails after step 2 leaves an image with no git tag; the next
run computes the same version and overwrites it.

## This Repo

This repository follows the same pattern it encourages elsewhere:

* `validate.yaml` runs lightweight checks on pull requests
* `main.yaml` runs on `main`, re-validates, then runs semantic-release

That keeps pull request checks fast while still giving the shared workflows
repo its own versioned release flow.

`validate.yaml` takes one input:

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |

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

## Action Lint

`action-lint.yaml` installs actionlint with `go install` at
`actionlint-version` and lints the calling repository's workflows. Register
self-hosted runner labels in the caller's `.github/actionlint.yaml`.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. To register custom self-hosted runner labels with actionlint, commit a .github/actionlint.yaml file in the calling repo — see <https://github.com/rhysd/actionlint/blob/main/docs/config.md>. |
| `go-version` | string | `1.25.0` | Go version used to install actionlint |
| `actionlint-version` | string | `v1.7.12` | actionlint version to install |

## Cleanup GHCR

Container registry tags are mutable pointers; each push of a reused tag
(`:dev`, `:main`, a rebuilt `:vX.Y.Z`) leaves the previous manifest behind
as an untagged version. Those orphans accumulate forever unless something
deletes them. `cleanup-ghcr.yaml` does the deletion.

### What it does

For a single GHCR package, in two passes:

* **Pass 1 — build the protection set.** For every **tagged** manifest,
  fetch it and collect the child digests it references (a multi-arch image
  tags only its index; the per-architecture children and attestation
  manifests are untagged). These referenced children are always kept —
  deleting them would break the tagged pull.
* **Pass 2 — delete.** Keeps every **tagged** version (pruning those is the
  caller's call, not this workflow's), keeps every **untagged** version whose
  `updated_at` is within the retention window OR that is in the pass-1
  protection set, and deletes everything else.

**Fails closed.** If any tagged-manifest fetch or parse in pass 1 errors, the
protection set may be incomplete, so the run skips all deletions (degrades to
report-only) **and exits non-zero** — a persistently broken protection pass
surfaces as a job failure rather than silently pruning children that a tagged
index still references.

Every run writes a job summary with the counts (kept tagged, kept recent,
deleted), and notes when it failed closed.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `package_name` | string | `""` | GHCR package name under the owner (defaults to the repository name). |
| `retention_days` | number | `7` | Keep untagged versions updated within this many days. |
| `owner_type` | string | `orgs` | Package owner type — "orgs" or "users". |
| `dry_run` | boolean | `false` | Log candidates without deleting anything. |

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

## Detect Changes

`detect-changes.yaml` outputs `changed=true` when any of the listed paths
changed between the triggering event's base and head commits, for
`pull_request` and `push` events. A base it cannot diff (branch creation, a
force push) reports `changed=true`, because running CI needlessly is the
cheap failure. Call it once per independent signal.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `paths` | string | required | Newline-separated list of git pathspecs to watch. Each entry can be a directory ("packer/"), a single file ("Dockerfile"), or a glob ("*.tf"). Output is "true" if any tracked file under any listed path changed between the event's base and head commits. |

### Outputs

| Output | Description |
| --- | --- |
| `changed` | "true" if any listed path changed, else "false". |

## Go Lint

`go-lint.yaml` runs `golangci-lint`, installed with `go install` at
`golangci-version`, and `gofmt`. A repository without its own golangci
config gets `golangci-default.yaml` from this repository, pinned to the
workflow's own commit. A third job fails when the Dockerfile's `golang:`
builder is older than the `go.mod` directive. `golangci-args` is shell words.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `go-version-file` | string | `go.mod` | Path to the Go version file |
| `vendor` | boolean | `false` | Run go mod vendor before linting |
| `golangci-args` | string | `--timeout=10m` | Arguments passed to golangci-lint |
| `golangci-version` | string | `v2.1.6` | golangci-lint version to install |

## Go Security

`go-security.yaml` runs `gosec` and `govulncheck`, each installed with
`go install` at a pinned version. govulncheck fails the job only for a
reachable vulnerability with a published fix; a reachable one with no fix is
a warning. `gosec-args` and `govulncheck-args` are shell words.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `go-version-file` | string | `go.mod` | Path to the Go version file |
| `gosec-args` | string | `-exclude-generated ./...` | Arguments passed to gosec |
| `gosec-version` | string | `v2.25.0` | gosec version to install |
| `govulncheck-version` | string | `v1.1.4` | govulncheck version to install |
| `govulncheck-args` | string | `./...` | Arguments passed to govulncheck |

## Go Unit Tests

`go-unit-tests.yaml` runs `go vet` and `go test` with the race detector,
uploads `coverage.out`, and fails when `go mod tidy` changes `go.mod` or
`go.sum`. `vet-command`, `test-command` and `tidy-command` are shell command
lines.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `go-version-file` | string | `go.mod` | Path to the Go version file |
| `vet-command` | string | `go vet ./...` | Command used for go vet |
| `test-command` | string | `go test -json -race -coverprofile=coverage.out ./... \| tee unit-tests.json` | Command used for go test |
| `tidy-command` | string | `go mod tidy` | Command used for go mod tidy validation |
| `check-go-mod-tidy` | boolean | `true` | Validate go mod tidy output |
| `upload-coverage` | boolean | `true` | Upload coverage.out as an artifact when present |

## Helm Automount Audit

`helm-automount-audit.yaml` renders the chart with `helm template` and lists,
in the job summary, every Deployment, StatefulSet, DaemonSet, Job, CronJob,
Pod and AutoscalingRunnerSet that does not set
`automountServiceAccountToken: false`. It reports and does not fail.

`template-args` is shell words: quotes and `$VARS` work as they would on a
command line. yq is checked against the SHA-256 its upstream release
publishes before it runs. To bump it, change `yq-version` and `yq-sha256`
together, taking the checksum from the release's `checksums` file as
described under [Promtool Rules](#promtool-rules).

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `chart-path` | string | required | Path to the Helm chart directory |
| `template-args` | string | `""` | Arguments passed to helm template (e.g., "-f values.yaml -f values/prod.yaml") |
| `release-name` | string | `audit` | Release name for helm template |
| `helm-version` | string | `v4.3.0` | Helm version used to render the chart |
| `yq-version` | string | `v4.52.5` | yq release to install (linux amd64 binary) |
| `yq-sha256` | string | `75d893a0d5940d1019cb7cdc60001d9e876623852c31cfc6267047bc31149fa9` | SHA-256 of yq_linux_amd64 for yq-version, from that release's `checksums` file (SHA-256 column, see `checksums_hashes_order`). Change it together with yq-version. |

## Helm Lint

`helm-lint.yaml` runs `helm lint` on `chart-path`. `lint-args` is shell
words, for example `-f values.yaml -f values/prod.yaml`.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `chart-path` | string | required | Path to the Helm chart directory |
| `lint-args` | string | `""` | Additional arguments passed to helm lint |
| `helm-version` | string | `v4.3.0` | Helm version used to lint the chart |

## Helm RBAC Audit

`helm-rbac-audit.yaml` renders the chart with `helm template` and fails when
any ClusterRole grants access to `secrets`, by name or through `*`. It has no
allowlist.

`template-args` is shell words: quotes and `$VARS` work as they would on a
command line. yq is checked against the SHA-256 its upstream release
publishes before it runs. To bump it, change `yq-version` and `yq-sha256`
together, taking the checksum from the release's `checksums` file as
described under [Promtool Rules](#promtool-rules).

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `chart-path` | string | required | Path to the Helm chart directory |
| `template-args` | string | `""` | Arguments passed to helm template (e.g., "-f values.yaml -f values/prod.yaml") |
| `release-name` | string | `audit` | Release name for helm template |
| `helm-version` | string | `v4.3.0` | Helm version used to render the chart |
| `yq-version` | string | `v4.52.5` | yq release to install (linux amd64 binary) |
| `yq-sha256` | string | `75d893a0d5940d1019cb7cdc60001d9e876623852c31cfc6267047bc31149fa9` | SHA-256 of yq_linux_amd64 for yq-version, from that release's `checksums` file (SHA-256 column, see `checksums_hashes_order`). Change it together with yq-version. |

## Node Build

`node-build.yaml` runs `npm ci` and `npm run <build-script>` in
`working-directory`, and can upload the build output as an artifact.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `node-version` | string | `22` | Node.js version to install |
| `working-directory` | string | `.` | Directory containing package.json |
| `build-script` | string | `build` | npm script name for the build step |
| `upload-artifact` | boolean | `false` | Upload the build output as a workflow artifact |
| `artifact-path` | string | `dist` | Path (relative to working-directory) to upload when upload-artifact is true |
| `artifact-name` | string | `build-output` | Name of the uploaded artifact |
| `artifact-retention-days` | number | `7` | Days to retain the uploaded artifact |

## Node Lint

`node-lint.yaml` runs `npm run <lint-script>` and `npm run <tsc-script>` as
two jobs.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `node-version` | string | `22` | Node.js version to install |
| `working-directory` | string | `.` | Directory containing package.json |
| `lint-script` | string | `lint` | npm script name for the linter |
| `tsc-script` | string | `tsc` | npm script name for TypeScript type checking |

## Node Security

`node-security.yaml` runs `npm audit` against `package-lock.json` at
`audit-level`, omitting the `audit-omit` dependency groups.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `node-version` | string | `22` | Node.js version to install |
| `working-directory` | string | `.` | Directory containing package.json |
| `audit-level` | string | `high` | Minimum severity that fails the build (low, moderate, high, critical) |
| `audit-omit` | string | `dev` | Dependency groups to omit from audit (e.g. dev, optional, peer) |

## Node Unit Tests

`node-unit-tests.yaml` runs `npm run <test-script>` and can upload
`coverage/` as an artifact.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `node-version` | string | `22` | Node.js version to install |
| `working-directory` | string | `.` | Directory containing package.json |
| `test-script` | string | `test` | npm script name for the unit test runner |
| `upload-coverage` | boolean | `true` | Upload coverage/ as an artifact when present |

## Packer Build

`packer-build.yaml` installs Packer and runs `packer init`, `packer validate`
and `packer build` for `packer_dir`. The `provider_token` secret is exported
under the env var name `provider_env_var` gives.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `semantic_version` | string | none | Semantic version to tag the snapshot |
| `env` | string | none | Environment name to tag the snapshot (dev, prod, ...). Forwarded to Packer as -var env=&lt;value&gt;. |
| `packer_dir` | string | `./packer` | Path to the directory containing the Packer config |
| `packer_version` | string | `1.14.3` | Packer CLI version to install |
| `provider_env_var` | string | required | Name of the env var the Packer provider expects for its API token (e.g. HCLOUD_TOKEN, DIGITALOCEAN_TOKEN). |
| `extra_vars` | string | `""` | Additional Packer variables as newline-delimited KEY=VALUE pairs. Values are forwarded verbatim via -var. |
| `force` | boolean | `false` | Pass -force to packer build so existing artifacts are overwritten instead of failing. Safe when the provider's artifact is not live-referenced after creation (e.g. Hetzner snapshots). |
| `only` | string | `""` | Forwarded to packer as -only=&lt;value&gt; to restrict the build to a subset of sources (e.g. "hcloud.microos-x86"). Leave empty to build every source defined in the packer config. |

### Secrets

| Secret | Required | Description |
| --- | --- | --- |
| `provider_token` | yes | Provider API token exposed as the env var named by provider_env_var. |

## Packer Test

`packer-test.yaml` runs `test_script` with the provider token exported under
`provider_env_var`, and `SEMANTIC_VERSION` and `ENV` set from the inputs.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `semantic_version` | string | none | Semantic version to test against |
| `env` | string | none | Environment name the image was tagged with (dev, prod, ...). Forwarded to the smoke test as $ENV so the snapshot selector matches the build. |
| `test_script` | string | `./packer/tests/smoke-test.sh` | Path to the smoke test script |
| `provider_env_var` | string | required | Name of the env var the smoke test expects for the provider API token (e.g. HCLOUD_TOKEN, DIGITALOCEAN_TOKEN). |

### Secrets

| Secret | Required | Description |
| --- | --- | --- |
| `provider_token` | yes | Provider API token exposed as the env var named by provider_env_var. |

## Packer Validate

`packer-validate.yaml` runs `packer init`, `packer fmt -check` and
`packer validate` with `validate_vars` for `packer_dir`.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `packer_dir` | string | `./packer` | Path to the directory containing the Packer config |
| `packer_version` | string | `1.14.3` | Packer CLI version to install |
| `validate_vars` | string | `hcloud_token=validation-dummy` | Packer variables passed to `packer validate`, as newline-delimited KEY=VALUE pairs (each forwarded verbatim via -var). Defaults to the hcloud dummy token so existing hcloud consumers are unchanged; override for configs that declare a differently named provider token variable, or set to an empty string for configs with no required vars. |

## Pre-Commit

`pre-commit.yaml` installs pre-commit 4.2.0 with pip and runs
`pre-commit run <args>`. Set `go-version` or `go-version-file`,
`node-version` (with `install-npm-deps` for hooks that shell out to `npx`) and
`install-helm` for hooks that need those tools. `args` is shell words.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `python-version` | string | `3.13` | Python version used to install pre-commit |
| `go-version` | string | `""` | Go version to install for system pre-commit hooks |
| `go-version-file` | string | `""` | Path to a go.mod file used to resolve the Go version |
| `node-version` | string | `""` | Node.js version to install for system pre-commit hooks |
| `install-npm-deps` | boolean | `false` | Run npm ci before pre-commit (requires node-version to be set) |
| `working-directory` | string | `.` | Directory containing package.json (used when install-npm-deps is true) |
| `install-helm` | boolean | `false` | Whether Helm should be installed for pre-commit hooks |
| `helm-version` | string | `v3.18.6` | Helm version to install when install-helm is enabled |
| `args` | string | `--all-files` | Arguments passed to pre-commit run |

## Promtool Rules

`promtool-rules.yaml` gates a chart's alert rules. It installs yq and
promtool (and lokitool when asked), checks each download against the SHA-256
its upstream release publishes before running it, then runs the calling
repository's rule test script.

The script owns the repo-specific part: which templates and values it
renders, and any extra checks. The workflow fails the job when:

* any download does not match its checksum;
* the script exits non-zero (a promtool failure included);
* any test file's `rule_files` pattern matches no file. promtool only warns
  about this and exits 0, and a test that expects no alert then passes
  against an empty rule set;
* the number of `SUCCESS` lines promtool printed differs from the number of
  `*.test.yaml` files at the top level of `tests-dir`.

That last check is the script's contract: it must run `promtool test rules`
exactly once over every `*.test.yaml` in `tests-dir`, and let promtool's
output through. A test file it skips or tests twice, or a promtool run over
files outside `tests-dir`, changes the count and fails the job.

```yaml
  alert-rules:
    name: Alert Rules Gate
    uses: kupecloud/github-workflows/.github/workflows/promtool-rules.yaml@<full-commit-sha>
    with:
      runs-on: kupe-small
      # Optional: lint LogQL rules with lokitool after the promtool tests.
      # loki-rules-script: scripts/lint-loki-rules.sh
```

To bump a tool, change its version and checksum inputs together. Take the
checksum from the release's own file: `checksums` for yq (the SHA-256 column
given by `checksums_hashes_order`), `sha256sums.txt` for Prometheus, and
`SHA256SUMS` for Loki.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `script` | string | `scripts/test-alert-rules.sh` | Repository script, run with bash from the repository root, that renders the chart's alert rules and runs `promtool test rules` over the test files. It must let promtool's output through: the gate counts promtool's per-file SUCCESS lines in it. |
| `tests-dir` | string | `tests/promtool` | Directory holding the promtool `*.test.yaml` files. The job fails unless promtool reported SUCCESS for every one of them. |
| `helm-version` | string | `v4.3.0` | Helm version used to render the chart |
| `yq-version` | string | `v4.52.5` | yq release to install (linux amd64 binary) |
| `yq-sha256` | string | `75d893a0d5940d1019cb7cdc60001d9e876623852c31cfc6267047bc31149fa9` | SHA-256 of yq_linux_amd64 for yq-version, from that release's `checksums` file (SHA-256 column, see `checksums_hashes_order`). Change it together with yq-version. |
| `prometheus-version` | string | `v3.5.0` | Prometheus release whose tarball supplies promtool |
| `prometheus-sha256` | string | `e811827af26d822afb09a4f28314f61b618b12cff5369835a67f674d8b46f39a` | SHA-256 of prometheus-&lt;version&gt;.linux-amd64.tar.gz for prometheus-version, from that release's `sha256sums.txt`. Change it together with prometheus-version. |
| `loki-rules-script` | string | `""` | Optional repository script that lints LogQL alert rules with lokitool. When set, lokitool is installed and the script runs after the promtool tests. Empty skips both. |
| `lokitool-version` | string | `v3.5.3` | Loki release whose zip supplies lokitool |
| `lokitool-sha256` | string | `6d70bf1581bce14d6a1337b5a3dd9ecee24fdeeeac019ac2ee3d7f456475cd35` | SHA-256 of lokitool-linux-amd64.zip for lokitool-version, from that release's `SHA256SUMS`. Change it together with lokitool-version. |

## Publish Image

`publish-image.yaml` builds `dockerfile` for `platforms` with Buildx, pushes
it to `ghcr.io/<owner>/<repo>` tagged `<version>`, `v<version>`,
`sha-<short>` and, on `main`, `main`, then signs the digest with cosign
keyless in the legacy `.sig` format. The caller grants `packages: write` and
`id-token: write`. See
[Digest-pinned image releases](#digest-pinned-image-releases).

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `version` | string | required | Semantic release version without the leading v |
| `platforms` | string | `linux/amd64,linux/arm64` | Target platforms for Docker buildx |
| `dockerfile` | string | `./Dockerfile` | Path to Dockerfile |
| `context` | string | `.` | Docker build context path |
| `build-args` | string | `""` | Docker build arguments (newline-separated KEY=VALUE) |

### Outputs

| Output | Description |
| --- | --- |
| `digest` | Manifest digest (sha256:...) of the pushed and signed image. Callers that build BEFORE semantic-release pass it to semantic-release.yaml's image-digest input so the release commit pins tag@digest. |

## Publish Node Image

`publish-node-image.yaml` is `publish-image.yaml` with `npm ci` and
`npm run <build-script>` first, for images that package a Node build such as
the Headlamp plugins.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `version` | string | required | Semantic release version without the leading v |
| `node-version` | string | `22` | Node.js version |
| `build-script` | string | `build` | npm script to run before Docker build |
| `platforms` | string | `linux/amd64,linux/arm64` | Target platforms for Docker buildx |
| `dockerfile` | string | `./Dockerfile` | Path to Dockerfile |
| `context` | string | `.` | Docker build context path |
| `build-args` | string | `""` | Docker build arguments (newline-separated KEY=VALUE) |

### Outputs

| Output | Description |
| --- | --- |
| `digest` | Manifest digest (sha256:...) of the pushed and signed image, for semantic-release.yaml's image-digest input (tag@digest release commits). |

## Semantic Release Preview

`semantic-release-preview.yaml` is a semantic-release dry run that outputs
whether the current commit would release and the next version. It needs
`contents: write`, because semantic-release checks that it could push even in
a dry run.

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |

### Outputs

| Output | Description |
| --- | --- |
| `new_release_published` | Whether a new release would be published |
| `new_release_version` | Next release version |

## Semantic Release

`semantic-release.yaml` runs semantic-release and creates the GitHub release.
It uses the repository's `.releaserc.json` when present and
`releaserc-default.json` from this repository otherwise. If `main` advanced
while the run queued, it fast-forwards first so the release is not silently
skipped. `image-digest` and `image-version` support
[Digest-pinned image releases](#digest-pinned-image-releases).

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `runs-on` | string | `ubuntu-latest` | Runner label. Defaults to ubuntu-latest. Override to a self-hosted runner label if you want to run CI on your own scale set. |
| `image-digest` | string | `""` | Digest (sha256:...) of an image already built and signed for this release. Exported to semantic-release as $IMAGE_DIGEST so a repo's @semantic-release/exec prepareCmd can stamp tag@digest into the release commit. Use with semantic-release-preview.yaml -&gt; publish-image.yaml (digest output) -&gt; this workflow. Empty = unset. |
| `image-version` | string | `""` | Version (no leading v) the image-digest was built for, exported as $IMAGE_VERSION. prepareCmd should fail unless it equals ${nextRelease.version}, so a digest can never be stamped onto a different release than the one it was built for. |

### Outputs

| Output | Description |
| --- | --- |
| `new_release_published` | Whether a new release was published |
| `new_release_version` | New release version |
