# AGENTS

Instructions for any coding agent working in this repository. `CLAUDE.md` has the same rules in full; this file is the entry point for other tools.

## Read first

1. `STATUS.md`: the live task board. Work the plan in priority order (the project is run solo) and do not mark a task done until its "Terminada cuando" is met.
2. The doc in `context/` that fits the task:
   - `context/approach.md`: what the project is, the method, scope.
   - `context/functions.md`: what each feature does and the acceptance checklist.
   - `context/structure.md`: architecture, repository layout, build and deploy.
   - `context/contracts.md`: field-by-field reference for the shared data files.
3. `CLAUDE.md`: commands, working method (`/drafter`, `/builder`, `/breaker`) and conventions in `.claude/rules/`.

If a doc and the code disagree, flag it; do not silently pick one.

## Hard rules

- Say "critical segment" (*tramo crítico*), "signal", "hypothesis". Never "confirmed closure" or "caused by rain", and never "works anywhere". The word "candidate" survives only as a key name in the data files (`candidates`).
- Product direction after the spikes (14 Nov, decision D8 in `STATUS.md`): consequence (criticality) with rain as context; not "risk = consequence × exposure". GCOV detection, SME2 and rain did not anticipate closures. The radar change layer is optional and may be empty. See `context/approach.md` §5.
- No fixed data as a seed: no Lanamme sites, MOPT kilometres or press coordinates to decide which segments matter. Press dates are validation labels only.
- The analysis area is a pipeline parameter (config), not a constant in code.
- Do not invent data: unknown values stay `null` or pending.
- Never commit raw NISAR data, large rasters or credentials.
- The pipeline and the frontend share only the data files; schemas live in `projects/contract/schemas/` and are frozen (change them as `context/contracts.md` §10 says). The contract is at 0.3.
- No backend, accounts or other regions without a team decision.
- Commits, code and error messages are in English; UI copy is Spanish.
