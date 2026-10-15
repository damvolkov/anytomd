# Development

The repository is a maturin project: a Rust crate at `crates/native` compiled into `anytomd._native`, re-exported by the `anytomd` package.

```text
crates/native/src/lib.rs     the binding: pyfunctions, classes, error mapping, asyncio bridge
src/anytomd/__init__.py      public surface
src/anytomd/_native.pyi      type stubs
tests/unit                   default suite
tests/stress                 threads, gather, ZIP bomb, hypothesis fuzzing
tests/integration            real LLM provider
tests/resources              fixtures (synthetic + real-world)
tools/                       fixtures, coverage, API diff and dependency health scripts
```

## Setup

```bash
uv sync            # venv + debug build of the extension
uv run prek install  # git hooks: pre-commit and pre-push
make build         # rebuild after editing Rust (debug)
make build-release # optimized build
```

## Hooks

[prek](https://prek.j178.dev) runs the same gates locally and in CI (`prek.toml`):

| Stage | Python | Rust | Repository |
|---|---|---|---|
| pre-commit | `ruff check`, `ruff format`, `ty`, `tach`, `validate-pyproject` | `cargo fmt`, `cargo clippy -D warnings` | whitespace, EOF, line endings, TOML/YAML/JSON, large files, private keys, licenses freshness, `zizmor`, `mkdocs --strict`, `gitleaks` |
| pre-push | unit suite + coverage gate | `cargo llvm-cov` ≥ 90 % lines | — |

```bash
uv run prek run --all-files                       # every pre-commit hook
uv run prek run --all-files --hook-stage pre-push # coverage gates
```

## Gates

```bash
make check         # ruff + ty + tach + build + unit tests
make stress        # concurrency and volume suite
make integration   # real image description through an LLM provider
make suite         # everything
make cov           # Rust line coverage driven by the Python suite (gate: 90 %)
make licenses      # regenerate THIRD_PARTY_LICENSES.md (CI fails when stale)
make docs          # strict documentation build
make serve         # live documentation on 127.0.0.1:8000
```

`make cov` needs `cargo-llvm-cov` and the `llvm-tools-preview` component; `make licenses` needs `cargo-about`.

The integration suite reads `ANYTOMD_LLM_BASE_URL`, `ANYTOMD_LLM_API_KEY` and `ANYTOMD_LLM_MODEL`, and skips when no key is set. Both Anthropic-style (`…/anthropic/v1`) and OpenAI-compatible endpoints are understood.

## Fixtures

```bash
make samples       # regenerate synthetic fixtures (tools/gen_samples.py)
make samples-real  # download real-world documents (tools/get_samples.py)
```

## Following a new anytomd-rs release

Automated → [Self-maintenance](maintenance.md). By hand:

1. Bump the pinned crate in `Cargo.toml` (`anytomd = { version = "=X.Y.Z", … }`), the workspace `version` and the `pyproject.toml` `version` to `X.Y.Z`.
2. `cargo update -p anytomd && uv lock && make licenses`.
3. `make apidiff OLD=<previous> NEW=X.Y.Z` and the release notes: mirror new options, formats, errors or warnings in `lib.rs`, the stubs, tests and these docs.
4. `make suite`.
