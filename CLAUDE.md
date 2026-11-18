# VANTAGE

VANTAGE shows which road segments of a road corridor, if cut, leave communities without a route to a referral hospital, and for how long; the method is designed for any corridor with an OSM road network, and Ruta 32 (Costa Rica) is the demonstration case and the only one tested; recent rain is shown as context. Three signal tests were negative (NISAR GCOV detection, SME2 soil moisture, rain before closures) and are reported as findings; the radar change layer is optional (decision D8 in `STATUS.md`). Entry for NASA Space Apps 2026, "Dancing with the SARs".

## Read first

Orientation lives in `context/`. Read the one that fits the task before changing anything:

- `context/approach.md`: what the project is, the method, scope and working principles.
- `context/functions.md`: what each feature does and the acceptance checklist.
- `context/structure.md`: architecture, repository layout, build and deploy.
- `context/contracts.md`: field-by-field reference for the data files shared by pipeline and web.

If a doc and the code disagree, flag it; do not silently pick one.

## Layout

Two pieces joined only by data files: an offline Python pipeline writes them, a static web app reads them.

- `projects/pipeline/`: Python, managed with `uv`.
- `projects/frontend/`: Bun, strict TypeScript, React and Vite. Code is in `source/`.
- `projects/contract/`: JSON Schemas and mock data for the shared files.
- Specs live flat in each project's `deltas/<slice>.spec.md`.

## Commands

Frontend, from `projects/frontend/`: `bun install`, `bun run dev`, `bun run build`, `bun run lint`.

Contract and pipeline, from the repo root: `make mock validate` (copy the mocks into `storage/` and validate every zone), `uv run --project projects/pipeline pytest`. `make all` is not implemented yet.

## Working method

Specs are living contracts, written in three steps: `/drafter <slice>` interviews and writes the spec, `/builder <slice>` plans and builds it test-first, `/breaker <slice>` tries to break what is built. Only trivial single-file work skips this. `.claude/rules/` holds the conventions and loads by path.

## Hard rules

- Never overclaim: say "critical segment" (*tramo crítico*), "signal", "hypothesis". Never "confirmed closure", "caused by rain" or "works anywhere". "Candidate" stays only as a key name in the data files.
- No fixed data as a seed (no Lanamme sites, MOPT kilometres or press coordinates to pick segments); the analysis area is a config parameter.
- Do not invent data: unknown values stay pending or `null`, never made-up numbers, dates or names.
- Never commit raw NISAR data, large rasters or credentials.
- No backend, accounts or other regions without a team decision.
- Commits, code, error messages and UI copy are in English (Space Apps requires English); place names keep their original Spanish.
- Pushing and pulling are denied by the permission policy.
