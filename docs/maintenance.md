# Self-maintenance

The binding keeps itself aligned with its dependencies. Deterministic bots detect and prepare every change; an LLM agent fills only the gaps a machine cannot close by rule; a human merges.

```mermaid
flowchart LR
  R[Renovate] -->|PR renovate/*| S[sync.yml: versions + licenses]
  S -->|push| C[CI: tests · coverage · API diff]
  C -->|red, or engine API grew| A[ai-fix.yml: Qwen agent]
  A -->|commit [ai-fix]| C
  C -->|green| H[Human review and merge]
  A -->|3 attempts used| N[label needs-human]
  M[health.yml, monthly] --> I[issue deps-health]
```

## Moving parts

| Piece | Kind | Does |
|---|---|---|
| `.github/renovate.json` | Deterministic | Opens PRs for new versions: anytomd-rs at once, PyO3 and tokio separately, Python tooling and Actions grouped. Its *Dependency Dashboard* issue also marks packages without a release for a year as abandoned. |
| `sync.yml` | Deterministic | On `renovate/*`: sets the package version to the new engine version and regenerates `THIRD_PARTY_LICENSES.md`. |
| `ci.yml` | Deterministic | prek hooks (the same as every local commit: ruff, ty, tach, rustfmt, clippy, licenses freshness, zizmor, gitleaks), tests on Linux/macOS/Windows × Python 3.12/3.14, Rust coverage (≥ 90 % of lines), docs. On `renovate/*` also the **upstream context**: public API diff of the two engine versions (`cargo public-api`) and their release notes. Logs are kept as artifacts for the agent. |
| `ai-fix.yml` | Agent | After CI on `renovate/*`: **fix** mode when CI is red, **expose** mode when CI is green but the engine's public API gained items. Runs Qwen Code under `QWEN.md`. |
| `health.yml` | Deterministic | First day of each month: checks every direct dependency for an archived repository, a vanished package, a last release older than 18 months, or no push in 12 months. Opens or refreshes one `deps-health` issue; closes it when all is well. |
| `release.yml` | Deterministic | On a `v*` tag matching the package version: wheels for five platforms, sdist, GitHub build provenance, PyPI via trusted publishing (with PEP 740 attestations). |

## Guard rails

- The agent never commits. The workflow does, and only files under `crates/native/src/`, `src/anytomd/`, `tests/`, `docs/`, `CHANGELOG.md` and `README.md`; anything else it touched is discarded and listed in the PR comment.
- The GitHub App has no `workflows` permission: no token in the pipeline can change `.github/`.
- At most three `[ai-fix]` commits per branch; then the PR gets `needs-human`.
- **Expose** mode runs once per PR. Runs triggered by a stale head are skipped.
- `workflow_run` is limited to same-repository `renovate/*` branches, so forks never reach the secrets.
- Nothing merges itself. Branch protection on `main` requires one human approval.

## Versioning

The package version is the engine version it embeds: anytomd-rs `1.3.1` ships as `anytomd 1.3.1`. Binding-only releases over the same engine add a post-release segment: `1.3.1.post1`, `1.3.1.post2`. `sync.yml` resets the version when the engine moves; `anytomd.__version__` always reports the engine.

## Setup

One-time, in the GitHub repository settings.

**GitHub App** (*Settings → Developer settings → GitHub Apps → New*), webhook off, installed on this repository only:

| Permission | Access |
|---|---|
| Contents | Read and write |
| Pull requests | Read and write |
| Issues | Read and write |
| Metadata | Read |
| Workflows | No access |

**Secrets and variables** (*Settings → Secrets and variables → Actions*):

| Name | Kind | Value |
|---|---|---|
| `APP_CLIENT_ID` | Variable | The App's *Client ID* |
| `APP_PRIVATE_KEY` | Secret | The App's private key (`.pem` content) |
| `QWEN_API_KEY` | Secret | Alibaba Model Studio key |
| `QWEN_BASE_URL` | Variable, optional | OpenAI-compatible endpoint; default `https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1` |
| `QWEN_MODEL` | Variable, optional | Default `qwen3.8-max` |
| `QWEN_CLI_VERSION` | Variable, optional | Pin `@qwen-code/qwen-code`; default `latest` |

**Elsewhere:** install the [Renovate](https://github.com/apps/renovate) app on the repository; on PyPI add a trusted publisher (`release.yml`, environment `pypi`); enable Pages with source *GitHub Actions*; protect `main` (one approval, required checks, no bypass for the App); create the labels `upstream-update`, `binding-update`, `tooling`, `ai-modified`, `needs-human`, `deps-health`.

## Running the pieces by hand

```bash
make apidiff OLD=1.3.0 NEW=1.3.1   # what the agent would see for that engine bump
make health                         # the monthly report, locally
make licenses                       # regenerate THIRD_PARTY_LICENSES.md
make cov                            # Rust coverage gate
```

`health.yml` and the Renovate dashboard both accept a manual run (*Run workflow* / the dashboard checkbox).
