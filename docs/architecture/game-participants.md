# Stable Game Participants

## Decision

M6.0C introduces `GameParticipant` as the stable identity of one logical participant inside one game. A participant owns the mutable account binding, seat, and game-time display-name snapshot. `GamePlayer` remains the result record for that participant.

`GameEvent` is not part of M6.0C. When events are introduced later, actor and target references should point to `GameParticipant`: a `User` can be renamed or absent for a guest, while a `GamePlayer` is a result row whose role is scoring rather than in-game identity.

## Responsibility Boundary

`GameParticipant` owns:

- game membership;
- optional `user_id` binding;
- optional seat number;
- `display_name_snapshot`;
- the stable ID reserved for future in-game references.

`GamePlayer` owns:

- role and faction;
- final survival and winner state;
- base, adjustment, and final score;
- result notes and `ScoreAdjustment` children.

The API continues to flatten `user_id` and `seat_number` into result-player responses for compatibility, but both values are projected from `GameParticipant`. They are no longer columns on `game_players`.

## Stability Contract

- Re-saving an unchanged row preserves both `GameParticipant.id` and `GamePlayer.id`.
- Editing the user binding, seat, role, faction, outcome, score inputs, or notes preserves both IDs.
- Adding a logical participant creates one participant and one result row.
- Removing a logical participant removes only that participant, its result row, and its adjustments.
- A participant cannot be referenced by another game, and each participant has at most one result row.
- `display_name_snapshot` is copied when an account is bound or replaced and does not follow later account renames.

## Deferred Work

M6.0C does not add guest-management UI, freeze game roles or formats, or create event records. M6.0D is expected to address play/result status separation and historical format snapshots before event-stream work begins.
