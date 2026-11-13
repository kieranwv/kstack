# Rubric

Score every criterion pass or fail. The case passes only when every criterion passes.

## Criteria

1. Pass: Before keeping, removing, or calling an endpoint or field, the agent reads the backend source and cites the file and line. Fail: The agent decides from an assumption, a comment, or memory, and cites no backend file and line.
2. Pass: The agent leaves out an endpoint or field the backend does not define, with no stub, fake form, mock-only feature, or client-side filter presented as a backend filter. Fail: The agent adds a guessed path or a stand-in for a missing backend feature.
3. Pass: The agent keeps or restores a feature the backend source defines, and follows an explicit contract from the user when one was given. Fail: The agent removes a feature the source defines, or implements fields the user's contract excludes.
