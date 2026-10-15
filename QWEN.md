# anytomd — maintenance agent instructions

`anytomd` is the Python binding (PyO3 + maturin) of the Rust crate `anytomd` (anytomd-rs, by developer0hye).
Your job: keep the binding aligned with new versions of its dependencies — above all the engine. You edit files;
the workflow commits. Anything you change outside the allowlist below is discarded automatically.

## Layout

| Path | Holds |
|---|---|
| `crates/native/src/lib.rs` | The whole binding: `#[pyfunction]`s, `#[pyclass]`es, `to_py_err` error mapping, asyncio bridge, `#[pymodule] _native` registration |
| `src/anytomd/__init__.py` | Public re-exports and `__all__` |
| `src/anytomd/_native.pyi` | Type stubs: the contract users see |
| `tests/unit/` | pytest suite, one file per surface (`test_convert_bytes.py`, `test_options.py`, `test_describer.py`, …) |
| `tests/resources/` | Fixtures; regenerate with `make samples`, never hand-edit binaries |
| `docs/` | MkDocs site; `docs/reference/*.md` documents every function, option, class and exception |
| `CHANGELOG.md` | Keep a Changelog; you write under `## [Unreleased]` |

The engine source of the pinned version is in `~/.cargo/registry/src/*/anytomd-<version>/` after `uv sync`.

## Allowlist

You may modify only: `crates/native/src/`, `src/anytomd/`, `tests/`, `docs/`, `CHANGELOG.md`, `README.md`.
Never touch `.github/`, `Cargo.toml`, `Cargo.lock`, `pyproject.toml`, `uv.lock`, `QWEN.md` or any version number.

## Rules

1. Keep the Python API backwards compatible. If upstream forces a break, do not make it: describe it under
   "Needs a human decision".
2. Every new public item exposed from Rust needs, in the same change:
   - the wrapper in `lib.rs` with a `///` doc comment (it becomes the Python docstring) and its registration in `_native`;
   - the re-export in `__init__.py` and `__all__`;
   - the typed entry in `_native.pyi`;
   - at least one test in `tests/unit/` exercising it through `import anytomd`;
   - its section in the matching `docs/reference/*.md` page: usage example with output, parameters table, raises table.
3. New `ConversionOptions` fields become keyword-only parameters on all four conversion functions, with the crate's
   default, in signature, stub, docs (`docs/reference/options.md`) and tests.
4. New `ConvertError` variants map in `to_py_err` to a new subclass of `ConvertError` created with
   `pyo3::create_exception!` and a docstring, exported like the others. New `WarningCode` variants map to a new
   snake_case string in `ConversionWarning::from`, and in the `WarningCode` literal of the stub.
5. Release the GIL around engine calls (`run_blocking` / the tokio runtime), exactly as existing functions do.
6. No `unsafe`, no `unwrap()`/`expect()` in new code; propagate `PyResult`.
7. Do not invent API. Use only what appears in `.ai-context/upstream-context/` or in the crate source in the registry.
8. Python code: no comments except a single `### reason` line where logic needs it; no `if/elif` chains; absolute
   imports; tests named `test_<target>_<scenario>`.
9. Add a line under `## [Unreleased]` in `CHANGELOG.md` for every user-visible change.

## Done means

```bash
uv sync && SKIP=licenses,gitleaks uv run prek run --all-files && make test
```

passes: every prek hook (ruff, ty, tach, rustfmt, clippy, zizmor, mkdocs strict) and the unit suite.

## Final summary format

### Upstream changes detected
### Changes applied to the binding
### Tests added or modified
### Needs a human decision
(or "Nothing")
