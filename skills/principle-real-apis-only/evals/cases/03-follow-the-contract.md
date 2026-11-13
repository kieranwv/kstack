## Prompt

The user gives this contract: read a student, with fields id and name, and no other fields. The backend source is in the workspace and also defines a nickname field. Build the form.

## Expected

The agent follows the contract. The form sends id and name only. It does not add nickname and does not call a path the contract does not name. It cites the backend file and line for the read it calls.
