# Immutable Game Format Context

## Boundary

`GameFormat` and `FormatRole` are mutable templates used while a game is scheduled. `GameFormatSnapshot` and `GameFormatRoleSnapshot` are the historical authority after play starts. A started game must never reinterpret its player count, role choices, or role metadata from the current template.

`Game.format_id` remains the source-template link and supports pre-start selection. It is frozen after play or result entry begins. The one-to-one snapshot copies all format fields and every role row without merging duplicate names. Source foreign keys are provenance only and use `ON DELETE SET NULL`; copied values remain usable when seed replaces source roles.

## Freeze Transaction

Explicit `POST /games/{id}/start` and the compatibility auto-start in `PUT /games/{id}/result-draft` both:

1. lock the Game row with PostgreSQL `SELECT ... FOR UPDATE`;
2. read the source format and all roles in one joined SQL statement while locking the parent format row;
3. validate active state, positive counts, role names, factions, and total role count;
4. insert one format snapshot and its role snapshots;
5. apply state/result changes, history, audit, and draft writes in the same transaction.

Validation or concurrency failure rolls back every side effect. The unique `game_id` constraint is the database backstop; normal serialization comes from the Game row lock. Calling the freeze helper again returns the existing snapshot without consulting or updating the source.

There is currently no role-edit API. The format parent lock plus one-statement joined read gives runtime freezes a self-consistent source view. Any future role editor must lock the same parent row before changing children.

## Authority And Immutability

`GET /api/v1/games/{id}/format-context` explicitly marks context as live or frozen. Result GET, PUT, submit, review, and revise use the snapshot whenever it exists. Scheduled games may preview live context, but auto-start creates the snapshot before validating or writing the draft.

Snapshots have no update or delete API. Application services never replace one, seed never rebuilds one, and only physical Game deletion cascades to it. This is service-level immutability; M6.0D2 intentionally does not add a database update trigger or canonical hash.

## Legacy Backfill

Migration `20260722_0009` snapshots games with play, result, submission, or confirmation evidence. `snapshot_origin=legacy_backfill` means only that the migration copied the template available at migration time. It cannot prove that this was the exact configuration used historically. Missing source formats abort migration with the game ID; missing or count-mismatched role sets are copied as found so anomalies remain inspectable.

## Deferred Work

Snapshots currently describe composition, not executable rules. They do not freeze role assignments or infer winners. M6.1 GameEvent should reference `GameParticipant` for actors/targets, use `play_status` for append eligibility, and use this snapshot as format context. A later ruleset key/version must be added by a new migration rather than rewriting existing snapshots.
