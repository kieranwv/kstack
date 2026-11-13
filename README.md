# kstack

Rules for AI coding agents, written as skills and tested with evals.

kstack is a small, strict rule set layered on [pstack](https://github.com/cursor/plugins/tree/main/pstack). pstack is the base: `/poteto-mode`, the playbooks, and its principles. kstack holds general rules pstack does not already state, the evals for those rules, and the checks under `scripts/`. Follow pstack's default branch. This repo does not pin a pstack version or commit.

Each rule exists because an agent got something wrong, and each one stays only while an eval proves agents follow it. Anything a script can enforce is moved out of prose and into CI.

## Principles

| Skill | Rule | pstack |
| --- | --- | --- |
| [verify-like-a-user](./skills/principle-verify-like-a-user/SKILL.md) | Before calling work done, run it the way a user would. A passing build is not done. | [prove-it-works](https://github.com/cursor/plugins/blob/main/pstack/skills/principle-prove-it-works/SKILL.md) |
| [verify-before-you-speak](./skills/principle-verify-before-you-speak/SKILL.md) | Never report a name, status, or result you have not checked. If you could not check it, say so. | |
| [single-writer](./skills/principle-single-writer/SKILL.md) | One owner writes each repo. Keep pull requests small, one change each. | [separate-before-serializing-shared-state](https://github.com/cursor/plugins/blob/main/pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md) |
| [designated-directory](./skills/principle-designated-directory/SKILL.md) | Write files only where you were told to. | |

An empty pstack cell means this repo does not treat that rule as an extension of a current pstack skill. `extends` in the skill frontmatter is the same list, and `scripts/check_refs.py` checks each name against pstack's default branch.

## How a rule gets in

A candidate rule must be durable, specific, and change what an agent does. If it fits an existing rule, it extends that rule instead. Screening criteria are in [docs/screening.md](./docs/screening.md).

1. If a lint, script, or permission can enforce it, build that instead of writing a rule.
2. Otherwise add `skills/principle-<slug>/SKILL.md`. When the rule builds on a pstack skill, set `extends` to that skill's directory name under `pstack/skills/`. Several names are separated by commas. Leave `extends` out when there is no pstack parent.
3. `status` is `active`, `retired`, or `moved`. A moved or retired rule keeps its number. `audience` defaults to `agent`; `author` and `both` are the other values.
4. Write `evals/rubric.md` before any case. At least three pass/fail criteria.
5. Add cases under `evals/cases/`: a prompt and the expected behavior, nothing else.
6. Run each case with a fresh agent and have a different model judge it. Fix the skill until every case passes, and rerun after every edit. `scripts/run_evals.py` is the runner. See [docs/eval-runner.md](./docs/eval-runner.md).

Rule numbers only grow. A retired rule is marked retired, never deleted or renumbered.

The shared parser is `scripts/ruleslib.py`. Call `load_skill` rather than reading frontmatter again.

## Layout

```text
skills/principle-<slug>/        one rule per folder: SKILL.md + evals/
scripts/ruleslib.py             parser and rule checks
scripts/check_skills.py         layout and numbering checks
scripts/check_refs.py           extends targets on pstack main
scripts/eval_hash.py            skill hash against the last eval record
scripts/run_evals.py            pluggable eval runner
scripts/check_public_content.py banned-term check
config/                         terms, id patterns, and eval model names
dist/rules.md                   generated, do not edit
```

## CI

Every PR must pass:

- `dist/rules.md` is up to date (`python3 scripts/generate_rules_doc.py`).
- Each skill's `name` matches its folder and it has a rubric and cases.
- Rule numbers are unique, contiguous, and never disappear.
- Every `extends` target is a skill directory on a shallow clone of pstack at `main`.
- Each `SKILL.md` matches `evals/eval-hash.json`. After a skill already has a record, editing it fails until `scripts/run_evals.py` records a new run. See [docs/eval-runner.md](./docs/eval-runner.md).
- `scripts/check_public_content.py` finds no configured term or id pattern outside `config/public-content.json` and the paths in `allow_paths`.
- markdownlint.
- gitleaks: no secrets in the repo.

## Install

Install pstack first, from its default branch, and keep updating it. Then install kstack.

### Cursor

pstack is in the Cursor marketplace:

```text
/add-plugin pstack
```

kstack is this repository. It has `.cursor-plugin/plugin.json` and a root `plugin.json`. It is not in the Cursor marketplace.

- Local: clone this repo and copy or symlink it to `~/.cursor/plugins/local/kstack`, then reload Cursor.
- Team marketplace: import `https://github.com/kieranwv/kstack`. Cursor reads `.cursor-plugin/plugin.json`.

### Claude Code

```text
/plugin marketplace add cursor/plugins
/plugin install pstack@cursor-plugins
/plugin marketplace add kieranwv/kstack
/plugin install kstack@kstack
```

Claude Code leaves auto-update off for third-party marketplaces, so a plugin stays on the revision you installed. Enable auto-update from `/plugin` if you want pstack and kstack to follow their default branches. To load one checkout for a single session, run `claude --plugin-dir /path/to/kstack`.

Fork it and replace the rules with your own.

## Credits

The method (failures become skills, rubric before cases, a separate judge model, review comments become hard constraints) comes from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack).

## License

MIT
