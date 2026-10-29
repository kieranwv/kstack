# kstack

Rules for AI coding agents, written as skills and tested with evals.

kstack is a small, strict rule set. Each rule exists because an agent got something wrong, and each one stays only while an eval proves agents follow it. Anything a script can enforce is moved out of prose and into CI.

## Principles

| Skill | Rule |
| --- | --- |
| [verify-like-a-user](./skills/principle-verify-like-a-user/SKILL.md) | Before calling work done, run it the way a user would. A passing build is not done. |
| [verify-before-you-speak](./skills/principle-verify-before-you-speak/SKILL.md) | Never report a name, status, or result you have not checked. If you could not check it, say so. |
| [single-writer](./skills/principle-single-writer/SKILL.md) | One owner writes each repo. Keep PRs small, one change each. |
| [designated-directory](./skills/principle-designated-directory/SKILL.md) | Write files only where you were told to. |

## How a rule gets in

A candidate rule must be durable, specific, and change what an agent does. If it fits an existing rule, it extends that rule instead.

1. If a lint, script, or permission can enforce it, build that instead of writing a rule.
2. Otherwise add `skills/principle-<slug>/SKILL.md`.
3. Write `evals/rubric.md` before any case. At least three pass/fail criteria.
4. Add cases under `evals/cases/`: a prompt and the expected behavior, nothing else.
5. Run each case with a fresh agent and have a different model judge it. Fix the skill until every case passes, and rerun after every edit.

Rule numbers only grow. A retired rule is marked retired, never deleted or renumbered.

## Layout

```
skills/principle-<slug>/        one rule per folder: SKILL.md + evals/
scripts/generate_rules_doc.py   builds dist/rules.md from every skill
scripts/check_skills.py         layout and numbering checks
dist/rules.md                   generated, do not edit
```

## CI

Every PR must pass:

- `dist/rules.md` is up to date (`python3 scripts/generate_rules_doc.py`).
- Each skill's `name` matches its folder and it has a rubric and cases.
- Rule numbers are unique, contiguous, and never disappear.
- markdownlint.
- gitleaks: no secrets in the repo.

## Use it

> TODO: packaging not decided. For now, copy the `skills/` folders you want into your agent's skills directory.

Fork it and replace the rules with your own.

## Credits

The method (failures become skills, rubric before cases, a separate judge model, review comments become hard constraints) comes from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack).

## License

MIT
