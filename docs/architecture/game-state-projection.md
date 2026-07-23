# Deterministic Game State Projection

## Three Semantic Layers

Wolfboard separates three kinds of information:

1. `GameEvent` is the fact ledger. It records that a vote, action, explicit
   outcome, phase marker, exile, or death was entered.
2. The M6.3A projector derives only state that follows directly and
   deterministically from the current effective ledger.
3. A future rules layer may interpret those records under a specific ruleset.

The derived-state response is recorded state, not an automated ruling. For
example, `hunter_shot`, `witch_poisoned`, and `wolf_kill_selected` are recorded
actions. They do not mark a participant out. Only an explicit `player_died` or
`player_exiled` event changes `is_active_in_game`.

## Pure Reducer Boundary

`project_game_state` accepts frozen projection DTOs and returns a frozen
`GameDerivedState`. It does not receive a SQLAlchemy Session or FastAPI request,
query or write a database, read the clock, acquire a lock, or mutate its input.
It sorts events by `(logical_sequence_no, id)`, so caller ordering does not
affect the result. `PROJECTOR_VERSION = 1` identifies the current semantics.

The ORM boundary in `game_state_service.py` loads Game, the format snapshot
header and role inventory, participants with their current GamePlayer result,
and active events. It then copies those values into DTOs before calling the
reducer. Current `recorded_role_name` and `recorded_faction` come from the
editable result record; events do not assign or transform roles.

## Input And Output

The context identifies the Game lifecycle, immutable format snapshot, snapshot
schema version, ledger head, and start/end timestamps. Participant input uses
stable `GameParticipant.id` plus the current result role/faction. Event input
contains only immutable fields needed by the projector.

The response contains:

- projection metadata and format identity;
- explicit phase state;
- participant exit records with event provenance;
- explicit sheriff and badge state;
- raw and unambiguous ballot tallies;
- recorded action counts and grouped action summaries;
- round/phase indexes and night-resolution records;
- non-fatal projection issues.

The response deliberately does not embed the original event collection or
claim a winner, legal action, remaining resource, current role assignment, or
rules-engine result.

## Explicit Phase Semantics

Only `phase_started` opens a phase and only a matching `phase_completed` closes
it. Ordinary night/day events update the last observed phase and round but do
not imply that a phase is open. Therefore a timeline with night actions and no
explicit start correctly returns `current_phase = null`.

Mismatched or repeated markers remain readable and produce issues. The reducer
never repairs the ledger or invents a transition.

## Participants And Recorded Exits

`player_exiled` creates an exile record. `player_died` creates a death record.
Either makes `is_active_in_game` false. Multiple exit records are preserved,
ordered by logical sequence, and reported as consistency issues.

Actions such as shooting, poisoning, self-explosion, or selecting a wolf kill
do not create an exit. Events involving a participant who already has an exit
record remain applied and receive an informational consistency warning because
whether the action is legal depends on rules outside M6.3A.

## Sheriff And Ballots

Candidate declaration and withdrawal maintain explicit recorded sets.
`sheriff_elected`, badge transfer, and badge destruction update the badge from
their explicit facts. Contradictory badge records use the latest explicit fact
while preserving issues and provenance.

Votes are grouped by vote kind, round, and ballot number. Arithmetic over
recorded weights is deterministic:

- `raw_tally` includes every active vote record;
- `computed_tally` is present only when every voter appears once;
- abstentions are retained but add no candidate weight;
- duplicate votes are not interpreted as vote changes;
- explicit ties, revotes, elections, and exiles remain separate facts.

The projector never elects the highest tally or exiles a participant on its
own. Vote changes must use GameEvent correction so only one active version
occupies the logical position.

## Recorded Actions And Night Resolution

The projector counts recorded seer checks, witch antidote/poison actions, guard
protections, hunter and wolf-king shots, wolf self-explosions, sheriff votes,
and exile votes. Names use `recorded_*_count`; they do not represent legal,
available, or remaining actions.

`night_resolved` is indexed with its supplied `no_public_death` and note. It
does not create, cancel, or reconcile death events. Multiple active night
resolution records are retained and reported.

## Projection Issues

Issues describe inconsistent recorded data without turning semantic conflicts
into HTTP 500 responses. Each issue has a stable code, severity, message key,
event and participant provenance, phase/round, and structured details. The
initial vocabulary covers:

- phase overlap, missing start, and mismatch;
- duplicate exits and actions involving already-out participants;
- sheriff/candidate/badge contradictions;
- duplicate votes, explicit tie mismatch, and multiple ballot outcomes;
- repeated night resolution;
- duplicate logical positions, unknown participants, unsupported event types,
  and cross-Game events;
- missing snapshots, participant-count mismatch, and recorded roles absent from
  the snapshot.

Unknown future event types produce `unsupported_event_type`, skip only that
event's state effect, and allow the rest of the historical game to project.
Adding a registered event requires adding an explicit reducer handler and test.

## Effective Prefixes

`GET /api/v1/games/{game_id}/derived-state` accepts the optional positive
`through_logical_sequence` parameter. It applies current active events whose
logical sequence is at or below that value. A corrected event remains at its
original logical position, while a voided event is absent.

This is a prefix of the current effective timeline, not an as-of view of the
ledger before a correction or void. The M6.1 ledger updates old row status and
does not append an invalidation revision for void operations, so historical
as-of reconstruction would require a different ledger model.

## API, Permissions, And Read Consistency

The derived-state endpoint is read-only for admins and the assigned judge. It
can inspect any Game lifecycle state, including scheduled, cancelled,
submitted, confirmed, and revised history. An empty ledger returns an initial
state with every configured participant active and no invented phase, sheriff,
or exit.

The service uses fixed eager-loading queries and loads active events only. It
does not acquire `FOR UPDATE`, change `next_event_sequence`, or touch
`updated_at`. Under PostgreSQL's normal transaction behavior, a concurrent
append or correction may become visible between separate reads.
`event_ledger_head_sequence` is the Game's allocated ledger head observed by
the request; it is diagnostic metadata, not a strong ETag or materialized-state
revision.

## Snapshot Boundary And Deferred Rules

The immutable format snapshot supplies identity, player count, role inventory,
and schema version for consistency checks only. It does not prove which
participant held a role or whether an action was legal. Participant count and
recorded-role mismatches become issues rather than adjudication errors.

M6.3A does not persist checkpoints, write system events, infer resource
consumption, validate role powers, calculate deaths, or decide victory. M6.3B
will display this read-only state in the judge workbench. Future rules engines
must consume the fact ledger and deterministic projection without rewriting
GameEvent history.
