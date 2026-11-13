---
name: principle-real-apis-only
description: "Use when implementing, reworking, or auditing frontend changes, before choosing an endpoint or keeping or removing a feature. Call only backend endpoints and fields that exist."
rule: R5
status: active
---

# Real APIs only

## Rule

Build the frontend only against backend endpoints and fields that actually exist.

Never guess an endpoint, and never add a feature the backend does not support. If the backend lacks it, leave it out: no TODO stub, no fake form, no mock-only feature, and no client-side filtering presented as a backend filter. Decide whether an endpoint or field exists by reading the backend source, read-only, and cite the file and line. Before you remove or downgrade a feature, verify it in that source. Remove only what is absent. Restore anything you removed that the source defines. When the user gives an explicit contract, follow that contract.

## Why

A guessed endpoint fails against the real backend. A feature removed from an assumption deletes behavior the backend already supports.

## How to apply

- Before any edit, list each endpoint or field, the backend file and line that defines it, and whether you will keep it or remove it.
- Read the backend source without changing it. Cite the file and line from that read.
- When the source does not define the endpoint or field, leave the feature out.
- When a previous edit removed or downgraded a feature, check the source before leaving that edit in place. Restore what the source defines.
- When the user gives an explicit contract, follow it. Do not add endpoints or fields the contract leaves out.

## Failure examples

These are illustrations of the rule, not records of a particular task:

- An agent removed support for one student belonging to several groups. It assumed the backend lacked that support and did not read the backend source. The user pointed out that the support existed and that the source had not been read.
- The frontend posts to a path no backend file defines, and a TODO stub is left where the call would go.
- The client filters a list, and the change describes that filter as a backend filter. The backend source has no such filter.
