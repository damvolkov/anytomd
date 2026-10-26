# Development

A maturin project: the Rust crate at `crates/native` compiles to `anytomd._native`; the Python package follows the library triad — contracts inward, engines outward, use cases between.

```text
crates/native/src/lib.rs     the engine bridge: conversion, detection, image hooks, asyncio, error mapping
src/anytomd/__init__.py      the public surface: re-exports logic/api and the infra types
src/anytomd/infra/           contracts: errors, Document, DocumentWarning, specs, formats, routes
src/anytomd/backends/        engines: native (anytomd-rs), liteparse (PDF, OCR), openai (vision), registry
src/anytomd/logic/           use cases: api, conversion, detection, description, the image fallback
src/anytomd/config/          VisionSettings (ANYTOMD_VISION_*)
tests/unit/anytomd/          mirror of src/anytomd/
tests/stress                 threads, gather, ZIP bomb, hypothesis fuzzing
tests/integration            real vision model (ANYTOMD_VISION_*)
tests/resources              fixtures (synthetic + real-world)
tools/                       fixtures, coverage, text recovery and API diff scripts
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
| pre-commit | `ruff check`, `ruff format`, `ty`, `tach`, `validate-pyproject` | `cargo fmt`, `cargo clippy -D warnings` | whitespace, EOF, line endings, TOML/YAML/JSON, large files, private keys, licenses freshness, `zizmor`, `zensical build --strict`, `gitleaks` |
| pre-push | unit suite + coverage gate | `cargo llvm-cov` ≥ 90 % lines | — |

```bash
uv run prek run --all-files                       # every pre-commit hook
uv run prek run --all-files --hook-stage pre-push # coverage gates
```

## Gates

```bash
make check         # ruff + ty + tach + build + unit tests
make stress        # concurrency and volume suite
make integration   # the vision fallback and describe against a real model
make suite         # everything
make cov           # Rust line coverage driven by the Python suite (gate: 90 %)
make fidelity      # text recovery per format; fails on regression vs docs/fidelity.json (ARGS=--update rewrites it)
make licenses      # regenerate THIRD_PARTY_LICENSES.md (CI fails when stale)
make docs          # strict documentation build
make serve         # live documentation on 127.0.0.1:8000
```

`make cov` needs `cargo-llvm-cov` and the `llvm-tools-preview` component; `make licenses` needs `cargo-about`.

The integration suite uses the same configuration as the library, `ANYTOMD_VISION_MODEL`, `ANYTOMD_VISION_BASE_URL` and `ANYTOMD_VISION_API_KEY`, and skips without a model.

## Fixtures

```bash
make samples       # regenerate synthetic fixtures (tools/gen_samples.py)
make samples-real  # download real-world documents (tools/get_samples.py)
```

## Following a new anytomd-rs release

Automated → [Self-maintenance](maintenance.md). By hand:

1. Bump the pinned crate in `Cargo.toml` (`anytomd = { version = "=X.Y.Z", … }`); `ENGINE_VERSION` follows from `Cargo.lock` at build time.
2. `cargo update -p anytomd && uv lock && make licenses`.
3. `make apidiff OLD=<previous> NEW=X.Y.Z` and the release notes: mirror new options, formats or warnings in `lib.rs`, `backends/native.py`, `logic/api.py`, tests and these docs.
4. `make suite`.
