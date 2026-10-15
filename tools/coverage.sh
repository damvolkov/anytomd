#!/usr/bin/env bash
# Rust line coverage of the binding, driven by the Python suite (PyO3 guide recipe).
set -euo pipefail

THRESHOLD="${1:-90}"

eval "$(cargo llvm-cov show-env --sh)"
export CARGO_TARGET_DIR="$CARGO_LLVM_COV_TARGET_DIR"

cargo llvm-cov clean --workspace
uv run --no-sync maturin develop -q
uv run --no-sync pytest -m "not integration" -q -p no:randomly --timeout=300
cargo llvm-cov report --lcov --output-path coverage.lcov
cargo llvm-cov report --summary-only --fail-under-lines "$THRESHOLD"
