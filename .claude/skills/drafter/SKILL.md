---
name: drafter
description: >-
  Use to write or revise the contract of a slice, i.e. its deltas/<slice>.spec.md. It reads the real code, interviews the user about intent, scope, invariants and acceptance, and writes the spec as a living contract for the user to review. Trigger when the user wants to "spec out" a slice, write or harden a spec, or asks what a spec is missing, e.g. "let's spec out X", "write the spec for X", /drafter <slice>. Never builds code. Not for a trivial single-file slice with no invariant worth protecting.
argument-hint: <slice>
---

# Drafter

Code shows what a slice does today. It does not show why the slice exists, what is deliberately out of scope, what must never break, or what is intentionally undecided. Those only come from asking. This skill gets that missing half and writes it down as a living contract: claims with stable IDs, each with a way to verify it.

Its reason to change is "did we ask the right questions and find the right conflicts". Never "does the code satisfy the contract" (that is `builder`'s) or "can the implementation be broken" (that is `breaker`'s).

The slice is `$ARGUMENTS`; if empty, ask which slice. Interview the user in their language, but write the spec in English.

There is no CLI, no status field and no approval step in the files. The spec is a plain file at `<project>/deltas/<slice>.spec.md` (flat, no subfolders), and the user approves it by reading it and calling `/builder`.

---

## Step 0 — Read what already exists

- Find the `deltas/` folder of the project the slice belongs to (`projects/frontend`, `projects/pipeline` or `projects/contract`). If the owner is unclear, ask.
- If `deltas/<slice>.spec.md` exists, read it in full. Every question below must be about a real gap or an update, never something already answered.
- If it does not exist, confirm the slice's name and boundary with the user first, and decide whether it deserves a spec using `.claude/rules/when-write-deltas.md`: sized by capability, never by layer. If it does not clear that bar, say so and stop.

## Step 1 — Investigate the real implementation

Read the source that implements the slice: grep by the feature's name, walk its folder, read whole files rather than excerpts. Do not infer behavior from a filename or a doc's description. A slice with no code yet is fine: say so and work from the docs and the user.

While reading, compare the implementation with any project doc that describes the slice (`context/`) and with any project rule that applies. Note every mismatch. A doc that says one thing while the code does another is exactly the gap a contract exists to close, so it goes to Step 3, never resolved silently in either direction.

## Step 2 — Ask what the code alone cannot answer

For each point, confirm it from Step 1 or ask. Do not guess.

- **Intent:** why does the slice exist, in a sentence or two of domain language?
- **Scope and non-goals:** what is explicitly not this slice's job, especially anything a future contributor could assume belongs here?
- **Invariants:** what must hold however the implementation changes? This is the highest-value part, because it is what gets verified later. Phrase each as one EARS claim whose response can be observed (`When <trigger>, <subject> <response>`; also `While`, `Where`, `If … then`). If the wording is vague or joins two outcomes, ask what triggers it and what would be seen, and propose the rewrite.
- **Acceptance criteria:** each as `Given <context>, when <action>, then <outcome>`, only for what the invariants do not already cover.
- **Deferred / open questions:** what is intentionally undecided, and what event would decide it.
- **How each claim is verified**, which decides its tag:
  - `test: <command>`: a command that exits 0 when the claim holds. Name the file, package or folder it runs and do not filter by test name, so a filter that matches nothing cannot pass silently. Confirm the test exists before using this tag.
  - `manual`: only a person can check it.
  - `none`: nothing verifies it yet. It is valid, and it is also listed under Deferred as a testing gap.

Ask in a short, focused batch (`AskUserQuestion` when the choices are concrete) instead of the whole list at once. A spec built from two considered answers beats one built from five rushed ones; continue next turn if needed.

## Step 3 — Reconcile conflicts explicitly

Any mismatch from Step 1, and any answer that contradicts a doc, a rule or the current spec, is surfaced and resolved with the user before it goes into the spec. Never silently pick the code's version or the doc's. Fold the resolution into the spec, noting which side won and why. There is no separate decision log.

## Step 4 — Write the spec

1. Start from `.claude/skills/drafter/template.md`: copy it to `deltas/<slice>.spec.md` and replace `<slice>` with the bare slice name. Revising an existing spec edits it in place.
2. Each claim is a header line `- INV-01 [tag]` or `- ACC-01 [tag]`, and under it, indented, its one sentence. IDs are stable: never renumber a claim, and never reuse the ID of one you removed.
3. Self-check before handing over:
   - Every claim has exactly one sentence, one observable response and a valid tag.
   - Every `none` claim appears under Deferred as a testing gap.
   - Nothing in Scope contradicts the Contract.
   - The spec describes behavior, not implementation.
4. Language follows `.claude/rules/code-english-only.md`: error messages quoted in the spec are in English.

Then stop. Tell the user the spec is ready for review, summarize the claims, and name which are `none` or `manual`. The next step is `/builder <slice>`, which the user runs once they are happy with it.

---

## Non-goals

- Does not write code or tests; it ends at the spec.
- Does not re-ask what the current spec already settles.
- Does not force every field to a firm answer. "Intentionally undecided until X" is a complete answer for Deferred; a premature decision makes the spec lie about its own certainty.
- Does not spec a trivial single-file slice with no invariant worth protecting.
- Does not edit docs, rules or `CLAUDE.md`; those are edited by a person.
