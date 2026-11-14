# Branch Name Conventions

This governs every git branch name created in this repository, by a person or by Claude. It applies globally, so it carries no `paths:` scope. Pull request titles and commit messages are out of scope.

---

## Format

- The name is `type/short-description`, lowercase, with words separated by hyphens: `feat/closure-simulation`.
- The type is one of the commit types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. Sharing the vocabulary with commit messages means a branch and its commits read as one story.
- The description is 2 to 5 words in the imperative or as a noun phrase, and the whole name stays under 50 characters, because longer names get cut in git UIs and terminals.
- Only lowercase letters, digits, hyphens and the single `/` after the type. No spaces, underscores, dots, uppercase or accents, because they break in shells, URLs and case-insensitive file systems.
- The name is in English, whatever language the team speaks day to day, for the same reason commit messages are.

## What goes in the description

- Name the capability or the problem, not the implementation: `fix/isolated-community-count`, not `fix/change-if-statement`.
- When the work belongs to a spec slice, use the slice name as the description: `feat/impact-scoring`, so the branch can be found from `deltas/<slice>.spec.md`.
- No names of people, ticket numbers or dates. They age badly and say nothing about the change.

## Lifecycle

- `main` is the only long-lived branch. Everything else is short-lived and branches off `main`.
- One branch per logical change, the same unit as a commit: a phase of work, not a single tweak. A branch that needs "and" to be described is probably two branches.
- Claude creates a branch before its first commit when it is on `main`, and never commits to `main` directly once the repository has its first commit.
- A branch is deleted after it is merged. Merging and pushing are the person's job: pushing stays denied by the permission policy.

---

## Non-goals

- Doesn't dictate commit messages, pull request titles or how a branch is merged.
- Doesn't cover tags or release names.
