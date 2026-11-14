# VANTAGE

VANTAGE shows which road segments of Ruta 32 (Costa Rica), if cut, leave communities without a good route to a hospital, and how exposed they are (rainfall, optional NISAR soil moisture): risk = consequence × exposure. Landslide-scale detection with NISAR GCOV was tested and is a NO-GO (G1, 14 Nov); the radar change layer is optional. Entry for NASA Space Apps 2026, "Dancing with the SARs".

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

The pipeline, the contract folder and the root `Makefile` do not exist yet; do not assume their commands.

## Working method

Specs are living contracts, written in three steps: `/drafter <slice>` interviews and writes the spec, `/builder <slice>` plans and builds it test-first, `/breaker <slice>` tries to break what is built. Only trivial single-file work skips this. `.claude/rules/` holds the conventions and loads by path.

## Hard rules

- Never overclaim: say "critical segment" (*tramo crítico*), "signal", "hypothesis". Never "confirmed closure", "caused by rain" or "works anywhere". "Candidate" stays only as a key name in the data files.
- No fixed data as a seed (no Lanamme sites, MOPT kilometres or press coordinates to pick segments); the analysis area is a config parameter.
- Do not invent data: unknown values stay pending or `null`, never made-up numbers, dates or names.
- Never commit raw NISAR data, large rasters or credentials.
- No backend, accounts or other regions without a team decision.
- Commits, code and error messages are in English; UI copy is Spanish.
- Pushing and pulling are denied by the permission policy.
