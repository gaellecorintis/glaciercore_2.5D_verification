# Cursor Rules

Project-scoped AI guidance for Cursor. Every contributor who clones this template gets these rules automatically — no per-developer setup required.

## File format

One rule per file, `kebab-case-name.mdc`, with YAML frontmatter:

```mdc
---
description: Short, specific summary. Used by Cursor to decide if the rule is relevant.
globs: simulations/**, dune_design/**
alwaysApply: false
---

Rule body in Markdown. Be concrete: reference real paths, scripts, and conventions
that live in this repo. Link to files with @path/to/file.py when useful.
```

## Activation modes

Pick exactly one per rule via the frontmatter:

| Mode             | Frontmatter                              | When it applies                                      |
| ---------------- | ---------------------------------------- | ---------------------------------------------------- |
| Always           | `alwaysApply: true`                      | Loaded on every request. Use sparingly.              |
| Auto-attached    | `globs: <patterns>` + `alwaysApply: false` | Loaded when a matching file is in context.         |
| Agent-requested  | `description: ...` (no globs, no always) | Loaded when Cursor judges the description relevant. |
| Manual           | none of the above                        | Loaded only when invoked by name (`@rule-name`).    |

## Conventions for this repo

- **One concern per rule.** A rule about plotting style should not also explain the GCP setup.
- **Reference real artifacts.** Point at scripts in `scripts/`, styles in `utils/plotting_styles/`, configs in `dune_design/`, etc. Rules that paraphrase the README add noise.
- **Keep bodies short.** A rule is a nudge, not a manual. If something needs a page of explanation, put it in `README.md` and link to it.
- **Prefer auto-attached over always-on.** Always-on rules cost context on every request; scope with `globs` whenever possible.
