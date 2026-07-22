# Game State Machines

## Why Two States

M6.0D1 separates the physical game lifecycle from result review. `Game.play_status` answers whether gameplay may occur; `Game.result_status` answers whether a result exists and where it is in review. Code must not infer one dimension from the other.

```text
Play:   scheduled -> in_progress -> ended
        scheduled/in_progress -> cancelled

Result: empty -> draft -> submitted -> confirmed
                  ^          -> rejected
                  |               |
                  +---------------+
        submitted/confirmed/revised -> revised
```

## Transition Operations

| Operation | Play transition | Result transition | Endpoint |
| --- | --- | --- | --- |
| Start | scheduled -> in_progress | none | `POST /games/{id}/start` |
| End | in_progress -> ended | none | `POST /games/{id}/end` |
| Cancel | scheduled/in_progress/eligible ended -> cancelled | none | `POST /games/{id}/cancel` |
| First draft save | scheduled -> in_progress | empty -> draft | `PUT /games/{id}/result-draft` |
| Save after rejection | none | rejected -> draft | `PUT /games/{id}/result-draft` |
| Submit | in_progress -> ended when needed | draft -> submitted | `POST /games/{id}/submit-result` |
| Reject | none | submitted -> rejected | `POST /games/{id}/reject-result` |
| Confirm | none | submitted -> confirmed | `POST /games/{id}/confirm-result` |
| Revise | none | submitted/confirmed/revised -> revised | `POST /games/{id}/revise-result` |

Admins and the assigned judge may start or end. Cancellation is admin-only and requires a non-blank reason. Submitted, confirmed, or revised results cannot currently be cancelled because doing so requires an explicit ScoreLog void workflow.

## Transactions And History

Each state operation locks the Game row with PostgreSQL `SELECT ... FOR UPDATE`, reloads the state, validates the transition, and writes all side effects in one transaction. A stale waiter receives `409 Conflict` and leaves no partial records.

`GameStatusHistory.status_scope` is either `play` or `result`; `transition_key` names the domain operation. A history row is written only when the value changes. Therefore repeated `revised -> revised` corrections retain ResultConfirmation and AuditLog records without producing misleading same-value status history.

Audit snapshots include both states and all lifecycle, submission, confirmation, and cancellation metadata.

## Configuration Freeze

New `scheduled + empty` games may change their game number, format, and game type. Once play or result entry begins those fields are frozen; table, assigned judge, and notes remain operationally editable. Cancelled games are read-only. M6.0D2 freezes the selected format into immutable historical snapshots in the same start transaction.

The first draft save still auto-starts a scheduled game for compatibility with the current judge UI. M6.1 GameEvent entry will use `play_status` directly to decide whether normal gameplay events may be appended and will make start explicit.
