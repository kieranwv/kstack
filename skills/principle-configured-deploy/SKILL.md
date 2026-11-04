---
name: principle-configured-deploy
description: "Use after a release reaches the main branch. Let the configured auto-deploy publish it."
rule: R5
status: active
---

# Configured deploy

## Rule

After a release is pushed to the main branch, let the configured auto-deploy handle it. Do not run the deploy pipeline or the CDN by hand unless the user asks.

## Why

That push already starts the publish configured for the main branch. A manual run races that publish.

## Failure examples

These are illustrations of the rule, not records of a particular task:

- The agent starts a deploy after the release is already on the main branch.
- The agent purges the CDN without being asked.
