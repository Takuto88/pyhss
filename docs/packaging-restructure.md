# PyHSS Packaging Restructure Plan

Status: proposed, not yet executed. Each commit must stay green
(`pytest -xvv`, `ruff check`, `ruff format --check`).

## Background

Three import systems coexist in the tree today:

1. Flat top-level imports + `sys.path.append(.../lib)` in each entry
   script — what actually runs (docker, upstream systemd, direct runs).
2. The setuptools `package-dir pyhss = ""` mapping — used only by
   pip/debian/entry points; no source file ever imports `pyhss.*`.
3. pytest `pythonpath = "lib"` — a third mechanism for tests.

Consequences:

- The declared package name `pyhss` is dead in code; entry points and
  the dynamic version are the only consumers.
- PyCharm only resolves imports via an untracked manual Sources Root
  (`.idea/pyhss.iml`); fresh clones and other tools flag every import.
- Installed top-level module names (`version`, `utils`, `metrics`,
  `database`, ...) are collision-prone and can be shadowed by other
  packages, since `lib/` is appended to the end of `sys.path`.
- After install, the same files are importable under two module
  identities (`pyhss.lib.diameter` and top-level `diameter`), risking
  duplicate globals/classes the moment anything imports both forms.
- `tools/` is incoherent: one script has a `sys.path` hack, the rest
  rely on cwd, and `pyhss.tools` is declared installable although the
  tools are dev-only.

## Goals

- A real `pyhss` package in a `src/` layout; all internal imports are
  `pyhss.*`.
- Zero `sys.path` hacks except a small bootstrap that preserves direct
  script execution (`python3 hssService.py`).
- `tools/` stays at the repo root and is not installed.
- `config.yaml`, `docs/`, `debian/`, `docker/`, `systemd/`, `tests/`
  and the top-level files stay at the repo root.
- PyCharm/ruff/pytest/CI resolve everything from `pyproject.toml`
  alone.

## Decisions

- Keep raw script runs in docker and the upstream systemd units
  (bootstrap approach); do not switch them to pip console scripts.
  (Debian already uses console scripts via its drop-in overrides.)
- One PR: plan doc + C1 + C2. C3 hygiene is a separate follow-up PR.
- `tools/` is dev-only and excluded from the wheel.
- `src/` layout, not `pyhss/` at the repo root (keeps config/tests/
  packaging files out of the package and is auto-detected by
  PyCharm/ruff/mypy).

## Target layout

```
pyhss/                        (repo root — unchanged)
├── src/
│   └── pyhss/                ← was lib/
│       ├── <lib files>
│       ├── gsup/             (protocol/, controller/, ussd.asn1)
│       └── services/         ← was services/  (+ new __init__.py)
├── tools/                    (stays at root, dev-only, not installed)
├── tests/
├── config.yaml
├── pyproject.toml            (edited)
├── requirements*.txt
├── debian/  docker/  systemd/  docs/
├── CHANGELOG.md  README.md  LICENSE
```

Only `lib/` and `services/` change location.

## C1 — Mechanical migration

1. Moves:
   - `git mv lib src/pyhss`
   - `git mv services src/pyhss/services`
   - Add `src/pyhss/services/__init__.py` (SPDX header only, matching
     `lib/__init__.py`).
2. Import codemod. Files: `src/pyhss/**/*.py`, `tools/*.py`,
   `tests/*.py`. Exact, case-sensitive module list:
   `banners, baseModels, CryptoTool, database, databaseSchema,
   diameter, diameterAsync, gsup, logtool, lte, metrics, messaging,
   messagingAsync, milenage, pyhss_config, rat, S6a_crypt, utils,
   version`
   - `import X` → `import pyhss.X` (aliases preserved, e.g.
     `import diameter as DiameterLib` in tests)
   - `from X[.sub...] import ...` → `from pyhss.X[.sub...] import ...`
     (incl. indented local imports, e.g. tests/test_pyhss_config.py)
   - Verified: no stdlib/third-party import collides with the list;
     `version` appears only as `from version import pyhss_version`
     (services/apiService.py).
3. Bootstrap replaces every `sys.path.append` line (8 services):

   ```python
   if __package__ in (None, ""):
       sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
   ```

   For `src/pyhss/services/x.py`, `parents[2]` is `src/` in the source
   tree and `site-packages/` in an installed venv — one expression for
   both layouts.
   Tools (repo root): insert
   `Path(__file__).resolve().parent.parent / "src"` instead; replace
   the existing hack in tools/hss_Async_client.py.
4. `pyproject.toml`:
   - `package-dir` → `pyhss = "src/pyhss"`; replace the explicit
     `packages` list with `[tool.setuptools.packages.find]
     where = ["src"]` (tools excluded automatically); keep
     `package-data "* = [*.asn1]"`.
   - Dynamic version attr → `pyhss.version.pyhss_version`.
   - pytest: `pythonpath = "lib"` → `"src"`; keep the `PYHSS_CONFIG`
     env.
   - ruff: `include` paths `lib/...` → `src/pyhss/...` (scope
     unchanged); add `src = ["src"]`.
5. Path fixes:
   - `src/pyhss/pyhss_config.py`: config fallback
     `Path(__file__).resolve().parent.parent / "config.yaml"` →
     `parents[2] / "config.yaml"` (still lands on the repo root).
   - `tests/conftest.py`: `PYTHONPATH` env → `top_dir/src`; the three
     subprocess fixtures → `top_dir/src/pyhss/services/*.py`.
6. Verification gate:
   - `pytest -xvv`, `ruff check`, `ruff format --check`
   - `pip wheel .` → inspect contents: `pyhss/**` present, `tools/`
     absent, `ussd.asn1` present
   - Scratch venv `pip install .` → smoke-run all 8 console scripts
   - Direct runs: `python3 src/pyhss/services/hssService.py` and each
     tool
7. Commit: `refactor(packaging): move to src layout with pyhss
   package`

## C2 — Runtime and packaging consumers

- `docker/Dockerfile`: `WORKDIR /opt/pyhss/services` →
  `WORKDIR /opt/pyhss/src/pyhss/services`. launch-container.sh is
  unchanged (script names are identical).
- `systemd/*.service`: `ExecStart=python3 src/pyhss/services/<x>.py`,
  `WorkingDirectory` → deploy root. Document that the deploy root must
  contain the source tree. Debian's drop-in overrides to console
  scripts are unaffected.
- `docs/databases.md` (5+ refs incl. diff headers),
  `docs/release.md`, README: `lib/...` → `src/pyhss/...`.
- Scan `.dockerignore` / `.gitignore` for stale `lib` references.
- Verify the Debian build (dh_virtualenv + in-venv pytest) — it is the
  only consumer of the installed layout.
- Commit: `refactor(packaging): update docker, systemd and docs to new
  layout`

## C3 — Follow-up PR (out of scope for this PR)

- Delete `src/pyhss/metrics.py` (imported nowhere; confirm no external
  references first).
- Expand ruff from the 11-file allowlist to the whole repo; fix
  fallout.
- Remove the manual Sources Root from `.idea/pyhss.iml` (local,
  untracked).
- Later, optional: normalize module names (`baseModels` →
  `base_models`, `S6a_crypt` → `s6a_crypt`, `CryptoTool` →
  `crypto_tool`), add console entry points for tools.

## Risks

- Codemod false positives — mitigated by the exact case-sensitive
  module list plus the full test gate.
- Debian test run has `pyhss` both installed (venv) and on
  `pythonpath` (src). One copy wins per process, so behaviour is
  consistent; verify via the deb build.
- `ussd.asn1` loads via a `__file__`-relative path
  (gsup/controller/ss.py) and is covered by `package-data` —
  unaffected by the move.
- `git mv` preserves history and blame.
- Console script entry points are unchanged and start resolving for
  real.

## Rollback

Branch-based; no data, schema, or API changes. Abandon the branch if
needed.
