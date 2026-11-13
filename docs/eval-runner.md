# Eval runner

`scripts/eval_hash.py check` compares each `SKILL.md` to `skills/<slug>/evals/eval-hash.json`. The hash is SHA-256 of that file's bytes. Newlines are not normalized. Rubric and case edits do not change the hash.

`basis` in the JSON is either `baseline` or `run`.

- `baseline` seals the hash without a model run. It is not an eval result, and `evals/last-run.md` must be absent.
- `run` means `scripts/run_evals.py` finished every case and wrote `evals/last-run.md` with the same hash.

## CI

CI runs:

```bash
python3 scripts/eval_hash.py check --base "origin/<base>"
```

The check fails when the recorded hash differs from `SKILL.md`. It also fails when the base branch already has `evals/eval-hash.json` for that skill, `SKILL.md` differs from the base, and the head record is not a `run` for the new bytes. Updating the JSON to `baseline` after such a change does not pass.

The first record for a skill may be `baseline`. That is how the current rules were sealed. The next edit of those `SKILL.md` files needs `scripts/run_evals.py`.

Editing the JSON by hand can satisfy the checker. The checker does not prove a model was called. When `last-run.md` appears, review that file.

## How to rerun

1. Put at least one candidate model name, and a judge model name that is not also a candidate, in `config/eval-runner.json`.
2. Set `KSTACK_EVAL_RUNNER` to a command. It is split on whitespace and is not passed to a shell.
3. Run `python3 scripts/run_evals.py`, or add `--skill <directory>` for one skill.

The command reads one JSON object from stdin:

```json
{"role": "candidate", "model": "<name from the config>", "prompt": "<text>"}
```

`role` is `candidate` or `judge`. The command writes one JSON object to stdout and nothing else:

```json
{"text": "<completion>"}
```

Stderr is ignored. A non-zero exit, a timeout (`KSTACK_EVAL_TIMEOUT` seconds, default 180), or stdout that is not that object aborts the skill and writes nothing for it.

If `KSTACK_EVAL_RUNNER` is unset, or the model config is empty, the command exits 2 and writes nothing.

## Method

The steps follow pstack's eval playbook on its default branch: [eval.md](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/eval.md). This repository does not pin that file.

1. The candidate prompt is the case `Prompt` section alone. `Expected` and the rubric are not sent.
2. Each candidate model receives that same prompt. The judge packet labels the replies Candidate A, Candidate B, and so on. Model names are not in that packet.
3. The judge scores that case's replies in one pass against `evals/rubric.md`.
4. A usable judge reply is only a `CASE <file>` line and one `<number> pass` or `<number> fail` line per rubric criterion, with no other lines. Anything else aborts the skill and writes nothing.
5. The command then writes `evals/last-run.md` and sets `basis` to `run`. A failed criterion is still a completed run. The hash check does not require every criterion to pass. The pass and fail list is in `last-run.md`.

## Assumption

pstack spawns candidate subagents and one judge from another model family through Cursor. This repository does not know which provider a maintainer will call, so the model call is the subprocess above. The assumption is that the command maps `model` to that provider's name, does not add an eval framing to a `candidate` request, and returns the model text in `text`.

Two parts of the playbook are not in this scaffold: candidates are called one after another rather than in parallel, and the script does not read agent transcripts. The judge is one case at a time because each case is already one prompt.

## What was not run

No model was configured when this gate was added. The `eval-hash.json` files in the tree are baselines. They are not scores, and there is no `last-run.md`.
