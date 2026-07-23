# Game Event Workbench

## Purpose And Boundary

The private workbench at `/judge/games/{game_id}/events` lets an assigned judge or admin record and audit the 22 V1 `GameEvent` types from a phone, tablet, or desktop. It presents Game lifecycle, frozen format, participants, the effective timeline, and the append-only ledger in one operator surface.

The workbench does not derive current game state. Phase and round are operator-entered values, initially prefilled from the most recent effective event. It does not infer living players, ability availability, phase order, vote outcomes, deaths, or winners. The backend remains authoritative for permissions, lifecycle gates, payload validation, same-Game references, idempotency, sequence allocation, correction, and voiding.

## Server-Driven Definitions

`GET /api/v1/game-events/definitions` serializes the backend `EVENT_DEFINITIONS` registry for authenticated judges and admins. Each item supplies allowed phases, required and allowed direct references, assigned visibility, allowed sources, schema version, normalized payload JSON Schema, and semantic hints for participant/event reference fields.

The frontend registry contains only presentation concerns: category, localized label, formatter, field renderer, and quick-pick priority. A runtime drift check requires the client and server event type sets to match exactly. An unknown server type is shown as an unsupported client contract instead of being silently omitted. Backend validation is still applied to every write.

## Composer And Participant Selection

The composer uses a finite set of controls required by V1: text, boolean, enum, positive integer, positive number, participant list, event reference, event-reference list, and a restricted participant-to-tally editor. It deliberately is not a general JSON Schema form engine and does not expose an unrestricted JSON textarea.

Actor and target pickers use `participant_id` as both submitted value and React identity. They display seat, display-name snapshot, username, and result role where available, and support search across those fields. A game with no participants still permits participant-free events and links to the existing result/participant editor; the workbench does not introduce a second participant editor.

## Idempotent Draft And Retry Lifecycle

Before the first submission attempt, the browser creates a UUID with `crypto.randomUUID()`. The normalized request, its stable fingerprint, the UUID, creation time, and form version are saved under:

```text
wolfboard:event-draft:v1:{game_id}
```

The record contains no JWT, password, full Game aggregate, or unrelated account data. Object keys and nullable fields are normalized before fingerprinting. A network error keeps the exact request and UUID for an explicit same-request retry. Editing any transmitted field abandons that pending request, and the next attempt receives a new UUID. Success clears the stored draft. A conflicting reuse of an ID returns `409`, triggers a remote refresh, and is never retried automatically.

On reload, a valid version-1 draft for the same Game is restored with an explicit banner and discard action. Invalid, incompatible, or different-Game records are ignored. A `storage` event from another tab only prompts a refresh; client tabs do not merge drafts or attempt to override server concurrency controls.

## Effective Timeline And Ledger

The effective tab contains only active versions ordered by logical sequence and grouped visually by round and phase. Corrected active versions retain links to the ledger identity they supersede. This view is suitable as future replay input but is not itself a replay-derived state.

The ledger tab contains active, superseded, and voided records in immutable ledger-sequence order. It shows logical sequence, client ID summary, creator, timestamps, supersession, and invalidation metadata. Status, event type, phase, round, and participant filters apply only to the records currently loaded; the UI states this scope and offers pagination rather than implying a global filtered result.

## Correction And Void

Correction reuses the composer in a focused dialog, prefills the active event body, keeps logical sequence read-only, requires a reason, and submits a new client ID. On success both views refresh and expose the old/new version relationship. A concurrent `409` does not overwrite the winner and refreshes the ledger.

Void requires a reason and explicit confirmation. The warning states that history is retained and only the effective timeline loses the event. No restore action is exposed. Both operations are available only for active rows and only when the backend lifecycle permits them.

## Lifecycle Modes

| Game state | Workbench mode |
| --- | --- |
| `in_progress` + `empty/draft/rejected` | live entry |
| `ended` + `empty/draft/rejected` | backfill entry |
| `scheduled` | read-only, start action available |
| `cancelled` | read-only |
| result `submitted` | read-only pending review |
| result `confirmed/revised` | frozen read-only ledger |

Start and end buttons call the existing Game endpoints. Ending requires confirmation and still permits backfill before result submission. The UI state is advisory; every mutation is revalidated by the backend.

## Responsive And Accessible Interaction

The surface is single-column with large touch targets and a sticky save action on small screens, then changes to a composer/timeline split at desktop width. Participant choices use readable seat cards rather than a wide table. Dialogs are full-screen on small screens, support Escape, establish initial focus, expose labels and field-error associations, and identify status and visibility with text in addition to color. Chinese and English use the same responsive constraints.

## Testing And Deferred Work

Vitest, React Testing Library, and jsdom cover request normalization, stable fingerprints, local draft round-trips, registry drift, formatter output, field validation, pending retry identity, correction/void dialogs, participant-empty mode, lifecycle locking, and tab switching. `npm run test` is part of the frontend CI quality gate.

M6.3 will add replay reducers and derived current state. M6.4 will add visibility-aware public and full replay projections. Multi-device live synchronization, polling, WebSocket/SSE, automatic rules, and confirmed-result event correction remain deferred.
