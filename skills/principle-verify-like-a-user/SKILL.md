---
name: principle-verify-like-a-user
description: "Use before calling work done. Run the change the way a user would, and do not treat a passing build as done."
rule: R1
status: active
---

# Verify like a user

## Rule

Before calling work done, run it the way a user would. A passing build is not done.

Run the path the user takes to see the change. For a page, open it and use the control. For a command, run that command with input a user would give. For a request, send it and read the response. For a library, run a caller a user would write. A passing build, typecheck, or unit test is supporting evidence. It does not replace that path.

## Why

The failure a user hits is often invisible to the build. Calling the work done at the build leaves that failure in place.

## How to apply

- Name the user-visible path before you run it.
- Run it, and judge the thing the user would see.
- When the path cannot be run, say what blocked it and leave that part of the work unfinished.

## Failure examples

These are illustrations of the rule, not records of a particular task:

- A page change is called done because the unit tests passed, and the page is never opened.
- A new command flag is checked only with a help listing, and the command itself is never run.
- A service change is called done because the project compiled, and no request is sent.
