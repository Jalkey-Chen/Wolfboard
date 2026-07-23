# Derived State Panel

## Purpose

The private panel in `/judge/games/{game_id}/events` helps the assigned judge
and admins inspect the deterministic M6.3A projection while recording or
auditing a game. Its heading explicitly identifies a projection derived from
effective events, with equivalent localized copy. The panel is not an
automated adjudicator and does not infer unrecorded deaths, skill effects,
phase transitions, or victory.

Raw `GameEvent` rows remain the facts, the backend projector remains the sole
derived-state authority, and game rules remain a separate future layer. The
frontend only sorts response collections, groups related records, resolves
labels, and renders provenance links.

## Latest And Prefix Modes

Latest mode requests:

```text
GET /api/v1/games/{game_id}/derived-state
```

Selecting "View state after this event" on an active effective event requests:

```text
GET /api/v1/games/{game_id}/derived-state?through_logical_sequence=N
```

The latter applies the current active versions through logical position `N`.
It is not ledger as-of replay: corrected positions use their current active
replacement and voided events remain absent. A selected position with no
active event is still a valid prefix boundary. The panel shows this distinction
and offers an explicit return-to-latest action.

An `AbortController` and monotonic request token prevent a slower, older prefix
request from replacing a newer selection. Append, correction, void, start,
end, focus, and manual refresh invalidate the current response. If prefix mode
is active, refresh preserves `N` and announces that the ledger changed.

## Display Semantics

Phase cards distinguish an explicitly open phase from the last observed event
phase. A night event alone never becomes "current night" in the UI.

Participant cards use the backend `is_active_in_game` value and describe it as
"no explicit exit record found" or "explicit exit record present". Exile and
death provenance are shown separately. Shot, poison, kill selection, and
self-explosion events are never converted into exits in the browser.

The sheriff card shows only explicit election, transfer, or badge-destruction
records. Ballot cards keep raw tally, computed tally, and explicit outcomes
separate. Duplicate-voter data remains ambiguous exactly as returned by the
projector; the browser never picks a last vote.

Recorded action counts are historical counts, not remaining resources,
legality checks, or ability availability. Round summaries index recorded
events and do not claim that a phase is complete.

## Projection Issues

Warning and info issues are grouped in a dedicated region. The client registry
contains localized titles and explanations for every M6.3A issue code. Unknown
future codes use a visible fallback and retain the technical code rather than
crashing or disappearing.

Issues are described as record inconsistencies or ambiguous interpretation,
not rule violations. Event, participant, phase, round, and detail references
remain available for investigation.

## Provenance And Pagination

Every projected event ID uses one provenance action. It switches to the
effective timeline or ledger, ensures the row is available, scrolls it into
view, transfers keyboard focus, and briefly highlights it. If an event is not
in the loaded page, the workbench fetches the existing event-detail endpoint
instead of silently doing nothing.

## Lifecycle, Failure, And Staleness

The panel is readable for scheduled, in-progress, ended, cancelled, submitted,
confirmed, and revised Games. A locked event ledger remains a readable
projection and is not presented as an administrator-confirmed rules result.

Derived-state loading has an independent error boundary. A `403`, `404`,
validation error, network failure, or server failure leaves the composer,
effective timeline, and ledger usable and gives the panel a retry action.
Cross-tab activity marks the projection as possibly stale; it does not merge
drafts or poll continuously. The shown refresh time is the browser request
completion time, not an event occurrence timestamp. The ledger head is
diagnostic metadata, not an ETag.

## Responsive And Accessible Presentation

Phones use top-level Compose, Timeline, Ledger, and Derived State tabs so three
long views are not rendered as one scroll. Tablets and desktops keep the
composer beside a tabbed viewing area. Participants, ballots, rounds, and
issues use wrapping grids or cards rather than fixed-width tables.

Tabs expose tab semantics, loading and sequence changes use live regions,
filters have labels, disclosure controls expose expansion state, and event
location is keyboard operable. Status, issue severity, and exit records always
include text rather than relying on color.

## Deferred Work

M6.4 will add visibility-aware projections and replay pages for players and the
public. Historical ledger as-of replay, checkpoints, a browser reducer,
automatic phase progression, skill legality, automatic death, victory
calculation, WebSocket/SSE updates, and post-confirmation event correction
remain outside this panel. A future rules engine may consume derived state but
must not rewrite the GameEvent ledger.
