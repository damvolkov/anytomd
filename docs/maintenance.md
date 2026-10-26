# Self-maintenance

The binding keeps itself aligned with its dependencies. Deterministic bots detect and prepare every change; an LLM agent fills only the gaps a machine cannot close by rule; routine updates merge themselves once every required check passes. Dependency health and security are watched from outside by [esteward](https://github.com/edamlabs/esteward), the maintenance engine of EDamLabs.

```mermaid
flowchart LR
  R[Renovate] -->|PR renovate/*| S[sync.yml: changelog + licenses]
  S -->|push| C[CI: tests · coverage · API diff]
  C -->|red, or engine API grew| A[maintenance.yml: Qwen agent]
  A -->|commit [maintenance]| C
  C -->|green, routine update| M[auto-merge]
  C -->|green, engine or PyO3| H[human merge]
  A -->|3 attempts used| N[label needs-human]
  E[esteward, daily] --> I[status issue + one issue per incident]
```

## What it touches

Every file the system may change, who changes it and with which tool. Anything not listed is human-only.

| Target | Files | Who | Tool | When |
|---|---|---|---|---|
| **Dependency pins** | `Cargo.toml` (`anytomd`, `pyo3`, `tokio`), `pyproject.toml` dependency groups, `.github/workflows/*` action digests, the Qwen CLI pin | Renovate | Renovate | A new release upstream |
| **Lockfiles** | `Cargo.lock`, `uv.lock` | Renovate, `sync.yml` | cargo, uv | With every pin change; monthly lock file maintenance |
| **Changelog: engine line** | `CHANGELOG.md` → `## [Unreleased]` | `sync.yml` | awk | The engine version changes |
| **Third-party licenses** | `THIRD_PARTY_LICENSES.md` | `sync.yml` | cargo-about | Any Rust dependency changes |
| **Binding code** | `crates/native/src/lib.rs`, `src/anytomd/` (infra, logic, backends) | `maintenance.yml` agent | Qwen Code, cargo, maturin | CI red, or engine API grew |
| **Python surface** | `src/anytomd/logic/api.py`, `src/anytomd/__init__.py`, `src/anytomd/_native.pyi` | `maintenance.yml` agent | Qwen Code | Something new is exposed |
| **Tests** | `tests/` | `maintenance.yml` agent | Qwen Code, pytest | Every change the agent makes |
| **Docs** | `docs/` (Zensical) except the `docs/fidelity.json` baseline, `README.md` | `maintenance.yml` agent | Qwen Code, zensical | Something new is exposed |
| **Changelog: binding lines** | `CHANGELOG.md` → `## [Unreleased]` | `maintenance.yml` agent | Qwen Code | Every user-visible change |
| **Health and security issues** | Issues labelled `esteward` (status) and `esteward-escalation` (one per incident) | esteward | GitHub, PyPI, crates.io, OSV | Daily |
| **PR comments and labels** | The Renovate PR | `maintenance.yml` | gh | After each agent run |

The agent's limits are enforced by the workflow, not by trust: its commit keeps only `crates/native/src/`, `src/anytomd/`, `tests/`, `docs/` (not `docs/fidelity.json`), `CHANGELOG.md` and `README.md`; renames are checked on both paths, and the App token cannot write `.github/`.

**Human-only:** the package version, release tags (`v*`), the release date in `CHANGELOG.md`, `.github/`, `QWEN.md`, `prek.toml`, build and tooling config, and merging engine and PyO3 updates.

## Moving parts

| Piece | Kind | Does |
|---|---|---|
| `.github/renovate.json` | Deterministic | Opens PRs for new versions: anytomd-rs at once, PyO3 and tokio separately, Python tooling and Actions grouped. **Merges itself** (GitHub auto-merge, after every required check): Python tooling, Actions, lock file maintenance, the Qwen CLI pin, runtime patch releases. **Never merges itself**: the engine, PyO3 and tokio. |
| `sync.yml` | Deterministic | On `renovate/*`: adds the engine line to the changelog, regenerates `THIRD_PARTY_LICENSES.md`. |
| `ci.yml` | Deterministic | prek hooks (the same as every local commit: ruff, ty, tach, rustfmt, clippy, licenses freshness, zizmor, gitleaks), tests on Linux/macOS/Windows × Python 3.12/3.14, Rust coverage (≥ 90 % of lines), docs. On `renovate/*` also the **upstream context**: public API diff of the two engine versions (`cargo public-api`) and their release notes. Logs are kept as artifacts for the agent. |
| `maintenance.yml` | Agent | After CI on `renovate/*`: **fix** mode when CI is red, **expose** mode when CI is green but the engine's public API gained items. Runs Qwen Code under `QWEN.md` against the organisation's OpenAI-compatible provider. |
| esteward | Deterministic, external | Daily: every watched dependency (archived or dormant repository, PEP 792 registry status, release age, yanked release, license change), OSV advisories on every package of `uv.lock` and `Cargo.lock` (RustSec unmaintained notices included), every action pinned by SHA. Contract: [`fleet/anytomd.toml`](https://github.com/edamlabs/esteward/blob/main/fleet/anytomd.toml). |
| `release.yml` | Deterministic | On a `v*` tag matching the package version: wheels for five platforms, sdist, GitHub build provenance, PyPI via trusted publishing (with PEP 740 attestations). |

## Guard rails

- The agent never commits. The workflow does, and only files under its allowlist; anything else it touched is discarded and listed in the PR comment.
- The GitHub App has no `workflows` permission: no token in the pipeline can change `.github/`.
- At most three `[maintenance]` commits per branch; then the PR gets `needs-human`.
- **Expose** mode runs once per PR. Runs triggered by a stale head are skipped.
- `workflow_run` is limited to same-repository `renovate/*` branches, so forks never reach the secrets.
- `main` requires a PR and every required check; auto-merge waits for them, nobody bypasses them.

## Versioning

The package has its own semver (`anytomd.__version__`); the engine it embeds is `anytomd.ENGINE_VERSION`. An engine bump never changes the package version by itself: `sync.yml` records it in the changelog, and the version is picked when releasing.

## Configuration

Set once at the organisation level (EDamLabs), shared by every repository:

| Name | Kind | Used by | Holds |
|---|---|---|---|
| `APP_CLIENT_ID` | variable | `sync.yml`, `maintenance.yml` | Client ID of the `eself-maintenance` GitHub App: commits that re-trigger CI |
| `APP_PRIVATE_KEY` | secret | `sync.yml`, `maintenance.yml` | Its private key |
| `SM_API_KEY` | secret | `maintenance.yml` | API key of the OpenAI-compatible model provider |
| `SM_BASE_URL` | variable | `maintenance.yml` | Base URL of that provider |
| `SM_MODEL` | variable | `maintenance.yml` | Model the agent runs on |
| `QWEN_CLI_VERSION` | variable, optional | `maintenance.yml` | Version of the Qwen Code CLI (the agent, not the provider); defaults to the pin Renovate bumps |

## Running the pieces by hand

```bash
make apidiff OLD=1.3.0 NEW=1.3.1   # what the agent would see for that engine bump
make licenses                       # regenerate THIRD_PARTY_LICENSES.md
make cov                            # Rust coverage gate
```

The Renovate dashboard accepts a manual run (its checkbox); esteward runs on demand from its own `fleet` workflow.
