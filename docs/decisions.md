# Decisions

### 2026-10-26 · The project moves to EDamLabs

**Decision.** `damvolkov/anytomd` is transferred to `edamlabs/anytomd`; documentation moves to
`edamlabs.github.io/anytomd`. The PyPI name stays `anytomd`.

**Evidence.** EDamLabs gathers the open-source bindings and services under one organisation, one GitHub App
(`eself-maintenance`), one set of provider settings (`SM_*`) and one maintenance engine (esteward). GitHub keeps
redirects from the old URLs; a PyPI project cannot be renamed, so the distribution name is kept.

**Rejected.** A new PyPI name (breaks every existing install for a cosmetic gain).

### 2026-10-26 · Routine updates merge themselves; health moves to esteward

**Decision.** Renovate merges Python tooling, GitHub actions, lock file maintenance, the agent's CLI pin and
runtime patch releases through GitHub auto-merge after every required check; the engine, PyO3 and tokio never
merge themselves. `health.yml` and `tools/health.py` are removed: esteward watches the dependencies daily
(`fleet/anytomd.toml`).

**Evidence.** The same policy runs on etrafilatura; esteward covers everything `health.yml` checked, plus PEP 792
status, license changes, OSV advisories and action pins.

**Rejected.** A human merging every green routine PR; two reports of the same facts.

### 2026-10-26 · Documentation built with Zensical

**Decision.** The site builds with Zensical (`zensical build --strict --clean`); `mkdocs.yml` stays the
configuration, read natively.

**Evidence.** Material for MkDocs is in maintenance until 2026-11-05 and MkDocs 2.0 drops plugins and theme
overrides; the existing site builds unchanged with Zensical 0.0.71.

**Rejected.** Pinning MkDocs 1.x on a framework leaving maintenance.
