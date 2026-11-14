# VANTAGE

NISAR radar shows where a hillside moved near Ruta 32 (Costa Rica); VANTAGE shows which communities lose a good route to a hospital because of it. Entry for NASA Space Apps 2026, "Dancing with the SARs".

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

Pipeline, from the repo root: `uv sync --project projects/pipeline`, `uv run --project projects/pipeline pytest`. Root `Makefile`: `make mock`, `make publish`, `make validate`; `make all` fails on purpose until P7.

## Working method

Specs are living contracts, written in three steps: `/drafter <slice>` interviews and writes the spec, `/builder <slice>` plans and builds it test-first, `/breaker <slice>` tries to break what is built. Only trivial single-file work skips this. `.claude/rules/` holds the conventions and loads by path.

## Hard rules

- Never overclaim: say "candidate", "signal", "hypothesis". Never "confirmed closure" or "caused by rain".
- Do not invent data: unknown values stay pending or `null`, never made-up numbers, dates or names.
- Never commit raw NISAR data, large rasters or credentials.
- No backend, accounts or other regions without a team decision.
- Commits, code and error messages are in English; UI copy is Spanish.
- Pushing and pulling are denied by the permission policy.
