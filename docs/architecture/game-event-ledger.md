# Structured Game Event Ledger

## Boundary

`GameEvent` records facts inside an already started Werewolf game: phase markers, player actions, votes, public outcomes, skills, and deaths. It does not duplicate Game creation, start/end/cancel transitions, result review, or scoring. Those remain authoritative in `Game`, `GameStatusHistory`, `ResultConfirmation`, `ScoreLog`, and `AuditLog`.

Normal appends are the facts themselves and therefore do not create duplicate AuditLog rows. Corrections and voids do write AuditLog because they change which ledger version is effective. Events never write GameStatusHistory; night/day belongs to the event ledger, while GameStatusHistory only tracks play and result state machines.

## Stable Context

Actor and target fields reference `GameParticipant`, not `User` or `GamePlayer`. A participant preserves the identity used inside one game even when its result row changes. Composite foreign keys require every direct participant reference to belong to the same Game. Payload participant and event references are checked by the service.

Once any event references a participant, result reconciliation cannot delete it or change its user/seat binding. This avoids silently reinterpreting history until a versioned participant-correction flow exists. `GameFormatSnapshot` supplies the frozen format context required before an event can be appended.

## Ordering And Versions

`Game.next_event_sequence` is allocated while holding a PostgreSQL `SELECT ... FOR UPDATE` lock on the Game row. `sequence_no` is immutable append order. `logical_sequence_no` is effective timeline position:

- a new fact receives the same sequence and logical sequence;
- a correction receives a new sequence but inherits the old logical sequence;
- effective reads sort by logical sequence, then ID;
- ledger reads sort every active, superseded, and voided row by sequence.

A partial unique index on `(game_id, logical_sequence_no) WHERE status = 'active'` permits historical versions while allowing only one effective version at a logical position. Correction first marks the old active row `superseded`, flushes, then appends the replacement with `supersedes_event_id`. A void marks the active row `voided` without allocating a new sequence. Neither transition can restore a row to active.

## Idempotency And Concurrency

`client_event_id` is optional and unique within a Game. A retry with the same normalized body returns the existing row without consuming a sequence. Reusing the key for different content returns `409`.

Append, correct, void, result submission, and result reconciliation serialize on the same Game row. State and permissions are revalidated after locking. Thus appends can serialize successfully with distinct sequences, while correction/correction and correction/void races have one winner. Database unique, partial-unique, composite-FK, and CHECK constraints remain the final backstop.

## Lifecycle And Visibility

Only an assigned judge or admin can read the M6.1 ledger. They can append, correct, or void while play is `in_progress`, or while play is `ended` and the result is `empty`, `draft`, or `rejected`. Scheduled, cancelled, submitted, confirmed, and revised combinations are locked. Rejection reopens a submitted ledger; confirmed/revised correction requires a future dedicated workflow.

The server registry assigns visibility and the public API cannot override it:

- `public`: information that is public during normal play;
- `postgame_full`: hidden during play and eligible for a future complete replay;
- `judge_only`: never automatically exposed by future replay projections.

M6.1 APIs only create `manual` rows. `system` and `imported` are reserved sources.

## V1 Taxonomy

All payload models reject unknown keys. Participant and event ID lists are unique and same-Game validated. V1 records supplied facts and does not validate role ability, phase order, death causality, or victory conditions.

| Event type | Phase | References | Payload | Visibility |
| --- | --- | --- | --- | --- |
| `phase_started` | night/day | none | `{}` | public |
| `phase_completed` | night/day | none | `note?` | public |
| `wolf_kill_selected` | night | target required, actor optional | `selection_note?` | postgame_full |
| `seer_checked` | night | actor/target required | `result_faction` | postgame_full |
| `witch_saved` | night | actor/target required | `potion: antidote` | postgame_full |
| `witch_poisoned` | night | actor/target required | `potion: poison` | postgame_full |
| `guard_protected` | night | actor/target required | `{}` | postgame_full |
| `night_resolved` | night | none | `no_public_death`, `note?` | public |
| `sheriff_candidate_declared` | day | actor required | `{}` | public |
| `sheriff_candidate_withdrew` | day | actor required | `{}` | public |
| `sheriff_vote_cast` | day | actor required, target optional | `ballot_no`, `vote_weight=1` | public |
| `sheriff_elected` | day | target required | `ballot_no`, `tally?` | public |
| `exile_vote_cast` | day | actor required, target optional | `ballot_no`, `vote_weight=1` | public |
| `vote_tied` | day | payload participants | `vote_kind`, `ballot_no`, `candidate_participant_ids` | public |
| `exile_revote_started` | day | payload participants | `ballot_no`, `eligible_participant_ids` | public |
| `player_exiled` | day | target required | `ballot_no` | public |
| `hunter_shot` | night/day | actor/target required | `trigger_event_id?` | public |
| `wolf_self_exploded` | day | actor required | `note?` | public |
| `wolf_king_shot` | night/day | actor/target required | `trigger_event_id?` | public |
| `sheriff_badge_transferred` | day | actor/target required | `reason?` | public |
| `sheriff_badge_destroyed` | day | actor required | `reason?` | public |
| `player_died` | night/day | target required, actor optional | `cause`, `source_event_ids?`, `public_note?` | public |

Death causes are `wolf_kill`, `witch_poison`, `exile`, `hunter_shot`, `wolf_king_shot`, `self_explosion`, and `other`. Every row uses `schema_version=1`. A future schema converter must dispatch by event type and schema version and append migrated/imported facts without rewriting historical JSON in place.

## APIs And Deferred Work

The private operator API provides list (`effective` or `ledger`), single read, append, correct, and void endpoints. It eagerly loads participant summaries and creators. Legacy games are not given synthetic historical events. `GET /api/v1/game-events/definitions` exposes the same registry used for write validation to authenticated judges and admins. Its normalized JSON Schema and semantic reference hints let clients render the finite V1 payload controls without becoming a second authority for phase, reference, visibility, or payload rules.

M6.2 provides the private judge/admin workbench described in `game-event-workbench.md`. M6.3 will derive current state through replay. M6.4 will expose visibility-aware public and full replay projections. Automated phase progression, night resolution, deaths, rule enforcement, and winner inference remain intentionally outside the ledger and workbench.
