---
name: principle-single-writer
description: "Use when changing a repository. One writer owns that repository, the work runs in a cloud agent, and each pull request is one change. Delete branches you created once the work is merged or abandoned."
rule: R3
status: active
---

# Single writer

## Rule

One owner writes each repo. Keep pull requests small, one change each.

The user decides who writes a repository. When this task gives you that repository, you are the writer until the user says otherwise. Another agent does not write to it at the same time. A pull request contains one change.

Do code work in a cloud agent by default. Do not operate on the user's own machine unless the user asks. When work is merged or abandoned, delete the branch you created for it. Do not leave that branch behind.

## Why

Two writers in one repository produce overlapping diffs and lost edits. A pull request that bundles unrelated changes is hard to review and hard to revert. Edits on the user's machine collide with the user's own files. A branch left behind looks like open work.

## How to apply

- Before the first edit, confirm the user gave you this repository for this task.
- When another agent is already writing that repository, stop and tell the user. Do not push onto a branch that agent opened.
- Keep each pull request to one change. A separate concern is a separate pull request.
- Leave files the change does not need untouched.
- Run the edits in a cloud agent unless the user asked you to use their machine.
- When the work is merged or abandoned, delete the branch you created.

## Failure examples

These are illustrations of the rule, not records of a particular task:

- A second agent opens a pull request that edits the same files as the agent already writing the repository.
- A bug fix and an unrelated refactor ship in one pull request.
- An agent keeps pushing after the user assigned the repository to another agent.
- The agent edits the repository on the user's machine when the user did not ask for that.
- A merged pull request still has the branch the agent created.
- The agent drops a task and leaves the branch it created.
