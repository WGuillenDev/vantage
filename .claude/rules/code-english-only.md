# Code Language Conventions

This governs the language used in code itself: identifiers, and any string a piece of code produces at runtime, error messages above all, regardless of what language the team communicates in day to day.


## English everywhere, including error messages

- Every identifier is written in English: classes, functions, variables, constants, files, modules, database objects and test names.
- Every string a class or function produces at runtime is written in English: thrown or returned error messages, validation messages, log lines and user-facing text.
- An English class name does not make a non-English thrown string acceptable. The rule covers messages as much as structure.
- Domain terms with no good English equivalent are named in English anyway; if the original term matters, record it in the project glossary, not in the identifier.

```ts
// Wrong
throw new Error("El saldo es insuficiente");

// Right
throw new Error("Insufficient balance");
```


## Non-goals

- Says nothing about the language of conversation with the user, commit messages (covered by their own rule) or any artifact outside the code itself.
