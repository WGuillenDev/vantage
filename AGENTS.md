# AGENTS

Instructions for any coding agent working in this repository. `CLAUDE.md` has the same rules in full; this file is the entry point for other tools.

## Read first

1. `STATUS.md`: the live task board. Work only on tasks assigned to your user and do not mark one done until its "Terminada cuando" is met.
2. The doc in `context/` that fits the task:
   - `context/approach.md`: what the project is, the method, scope.
   - `context/functions.md`: what each feature does and the acceptance checklist.
   - `context/structure.md`: architecture, repository layout, build and deploy.
   - `context/contracts.md`: field-by-field reference for the shared data files.
3. `CLAUDE.md`: commands, working method (`/drafter`, `/builder`, `/breaker`) and conventions in `.claude/rules/`.

If a doc and the code disagree, flag it; do not silently pick one.

## Hard rules

- Say "candidate", "signal", "hypothesis". Never "confirmed closure" or "caused by rain".
- Do not invent data: unknown values stay `null` or pending.
- Never commit raw NISAR data, large rasters or credentials.
- The pipeline and the frontend share only the data files; schemas live in `projects/contract/schemas/` and are frozen (change them as `context/contracts.md` §10 says).
- No backend, accounts or other regions without a team decision.
- Commits, code and error messages are in English; UI copy is Spanish.
