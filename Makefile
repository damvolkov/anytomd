.PHONY: build build-release test lint format types arch check cargo-fmt clean dist stress samples samples-real integration suite publish

build:            ## compile native extension into the venv (debug)
	uv run maturin develop

build-release:    ## compile native extension into the venv (release)
	uv run maturin develop --release

test:             ## unit suite with coverage gate
	uv run pytest --cov --cov-report=term-missing -q

stress:           ## concurrency and volume suite only
	uv run pytest -m stress -q -p no:randomly --timeout=300

integration:      ## real LLM provider integration suite
	uv run pytest -m integration -q --timeout=300

suite:            ## everything, one 100% coverage gate
	uv run pytest -m "" --cov --cov-report=term-missing -q --timeout=300

samples:          ## regenerate synthetic test fixtures
	uv run python tools/gen_samples.py

samples-real:     ## download real-world sample documents
	uv run python tools/get_samples.py

lint:             ## ruff check
	uv run ruff check src tests tools

format:           ## ruff format
	uv run ruff format src tests tools

types:            ## ty static type check
	uv run ty check src tests

arch:             ## tach import contracts
	uv run tach check

check: lint types arch build test ## full gate

cargo-fmt:        ## rustfmt the native crate
	cargo fmt

clean:            ## remove build artifacts
	rm -rf target dist .pytest_cache .ruff_cache htmlcov coverage.xml .coverage

dist:             ## build release wheels + sdist -> dist/
	uv run maturin build --release --sdist --out dist

publish:          ## build and upload to PyPI
	uv run maturin publish
