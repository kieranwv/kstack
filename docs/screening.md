# Screening

A candidate becomes a rule only when every criterion below is true.

- **Durable.** It stays right after this task is over.
- **Specific.** An agent can tell whether it followed the rule.
- **Merge first.** If it fits an existing rule, extend that rule instead of adding a new one.
- **Changes behavior.** Following it changes what an agent does on the next task.
- **Encode as a check when possible.** If a lint, a script, or a permission can enforce it, build that check instead of adding prose.

Rule numbers only grow. A retired rule is marked retired, never deleted or renumbered. A moved rule keeps its number and is marked moved.

`extends` names a pstack skill this rule builds on. Setting it does not by itself satisfy the criteria above.
