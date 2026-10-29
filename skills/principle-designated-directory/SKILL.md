---
name: principle-designated-directory
description: "Use before creating or editing files. Write only in the directory the user named for this task."
rule: R4
status: active
---

# Designated directory

## Rule

Write files only where you were told to.

The user names the directory for the task. That directory is the only place files are created or edited. A repository the user named counts as that directory. A file the user named is edited in place. Neighboring files stay untouched unless the user asked for them.

## Why

An agent that picks its own destination scatters notes, drafts, and edits into places the user did not open. Later tasks then mix those files into the wrong change.

## How to apply

- Take the directory from the user's request. Do not infer a second one from the shell's current directory, a previous task, or a sibling checkout.
- When the task needs a scratch file, put it inside the named directory and say that you did.
- When the destination is ambiguous, ask before writing.
- When a tool offers a default output path outside the named directory, override that path or skip the write.

## Failure examples

These are illustrations of the rule, not records of a particular task:

- The user asked for an edit in one repository, and the agent also wrote a summary into a second checkout.
- A generator saved its output in a personal directory because that was the tool's default.
- The user named a file, and the agent created a sibling file they did not ask for.
