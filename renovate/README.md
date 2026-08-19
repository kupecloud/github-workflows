# Shared Renovate preset

`default.json` is the org-wide Renovate policy for every `kupecloud` repo.

Consume it with:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["local>kupecloud/github-workflows//renovate/default"]
}
```

## Why it lives here and not in `kupecloud/renovate`

It used to live in `kupecloud/renovate`, which is **private**. A private preset
cannot be resolved by a **public** repo, so Renovate failed config resolution
and — by design, fail-closed — **stopped raising PRs entirely** for those repos:

```text
Error type: Cannot find preset's package (local>kupecloud/renovate)
As a precaution, Renovate will stop PRs until it is resolved.
```

The failure is silent: no Dependency Dashboard, no PRs, no branches, just an
`Action Required: Fix Renovate Configuration` issue nobody reads. It disabled
Renovate on every public kupecloud repo — including the shipped artifacts
`kupe-cli` and `terraform-provider-kupe` — for 18 days before it was noticed.

This repo is already public and already consumed by every repo, so hosting the
preset here fixes public repos without a new repo and without duplicating the
policy into each consumer (which would break the "one org-wide dial" property).

Policy docs, cadence design and runbooks stay in
[`kupecloud/renovate`](https://github.com/kupecloud/renovate) — only the machine-
readable preset lives here.

## Changing it

Validate before pushing:

```bash
npx --yes --package renovate -- renovate-config-validator renovate/default.json
```

See `kupecloud/renovate` for what the rules mean and
`runbooks/change-cadence.md` there for the cadence procedure.
