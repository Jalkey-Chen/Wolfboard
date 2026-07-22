"""Freeze and project immutable per-game format context."""

from copy import deepcopy
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import FormatRoleFaction, FormatSnapshotOrigin
from app.models.game import Game
from app.models.game_format import GameFormat
from app.models.game_format_role_snapshot import GameFormatRoleSnapshot
from app.models.game_format_snapshot import GameFormatSnapshot
from app.schemas.game_format_context import GameFormatContextRead, GameFormatContextRoleRead


FORMAT_SNAPSHOT_LOAD_OPTIONS = (
    selectinload(Game.format_snapshot).selectinload(GameFormatSnapshot.roles),
)


def _invalid_source(detail: str) -> None:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _load_locked_source_format(db: Session, format_id: int) -> GameFormat | None:
    """Read a self-consistent template and role set while locking its parent row."""

    statement = (
        select(GameFormat)
        .options(joinedload(GameFormat.format_roles))
        .where(GameFormat.id == format_id)
        .with_for_update(of=GameFormat)
    )
    return db.execute(statement).unique().scalar_one_or_none()


def _validate_runtime_source(game_format: GameFormat) -> None:
    roles = list(game_format.format_roles)
    if not game_format.is_active:
        _invalid_source("The selected game format is inactive and cannot be frozen.")
    if game_format.player_count <= 0:
        _invalid_source("The selected game format must have a positive player count.")
    if not roles:
        _invalid_source("The selected game format has no role definition.")

    supported_factions = set(FormatRoleFaction)
    for role in roles:
        if not role.role_name.strip():
            _invalid_source("Every role in the selected game format must have a name.")
        if role.role_count <= 0:
            _invalid_source(f"Role '{role.role_name}' must have a positive count.")
        if role.faction not in supported_factions:
            _invalid_source(f"Role '{role.role_name}' has an unsupported faction.")

    role_total = sum(role.role_count for role in roles)
    if role_total != game_format.player_count:
        _invalid_source(
            f"The selected game format expects {game_format.player_count} players "
            f"but its roles total {role_total}."
        )


def freeze_game_format(
    db: Session,
    game: Game,
    *,
    frozen_by_user_id: int | None,
    frozen_at: datetime | None = None,
) -> GameFormatSnapshot:
    """Return the existing snapshot or copy a validated source template once."""

    if game.format_snapshot is not None:
        return game.format_snapshot

    existing = db.scalar(
        select(GameFormatSnapshot)
        .options(selectinload(GameFormatSnapshot.roles))
        .where(GameFormatSnapshot.game_id == game.id)
    )
    if existing is not None:
        game.format_snapshot = existing
        return existing

    if game.format_id is None:
        _invalid_source("The game has no format to freeze.")
    source = _load_locked_source_format(db, game.format_id)
    if source is None:
        _invalid_source("The selected game format no longer exists.")
    _validate_runtime_source(source)

    snapshot = GameFormatSnapshot(
        game=game,
        source_format_id=source.id,
        format_key=source.format_key,
        format_name=source.format_name,
        player_count=source.player_count,
        category=source.category,
        description=source.description,
        is_system_preset=source.is_system_preset,
        source_format_updated_at=source.updated_at,
        snapshot_origin=FormatSnapshotOrigin.RUNTIME_FREEZE,
        snapshot_schema_version=1,
        frozen_at=frozen_at or datetime.now(timezone.utc),
        frozen_by_user_id=frozen_by_user_id,
    )
    for role in sorted(source.format_roles, key=lambda item: (item.display_order, item.id)):
        snapshot.roles.append(
            GameFormatRoleSnapshot(
                source_format_role_id=role.id,
                role_name=role.role_name,
                faction=role.faction,
                role_count=role.role_count,
                display_order=role.display_order,
                metadata_json=deepcopy(role.metadata_json),
            )
        )
    db.add(snapshot)
    db.flush()
    return snapshot


def authoritative_format(game: Game) -> GameFormatSnapshot | GameFormat:
    """Return frozen context when present, otherwise the scheduled live template."""

    if game.format_snapshot is not None:
        return game.format_snapshot
    if game.format is None:
        _invalid_source("The game has no available format context.")
    return game.format


def authoritative_format_roles(game: Game):
    context = authoritative_format(game)
    if isinstance(context, GameFormatSnapshot):
        return context.roles
    return context.format_roles


def build_game_format_context(game: Game) -> GameFormatContextRead:
    """Project a uniform API payload from frozen or live format rows."""

    context = authoritative_format(game)
    if isinstance(context, GameFormatSnapshot):
        return GameFormatContextRead(
            is_frozen=True,
            source_format_id=context.source_format_id,
            snapshot_id=context.id,
            snapshot_origin=context.snapshot_origin,
            snapshot_schema_version=context.snapshot_schema_version,
            format_key=context.format_key,
            format_name=context.format_name,
            player_count=context.player_count,
            category=context.category,
            description=context.description,
            is_system_preset=context.is_system_preset,
            frozen_at=context.frozen_at,
            frozen_by_user_id=context.frozen_by_user_id,
            roles=[
                GameFormatContextRoleRead(
                    id=role.id,
                    source_format_role_id=role.source_format_role_id,
                    role_name=role.role_name,
                    faction=role.faction,
                    role_count=role.role_count,
                    display_order=role.display_order,
                    metadata_json=deepcopy(role.metadata_json),
                )
                for role in context.roles
            ],
        )

    return GameFormatContextRead(
        is_frozen=False,
        source_format_id=context.id,
        snapshot_id=None,
        snapshot_origin=None,
        snapshot_schema_version=None,
        format_key=context.format_key,
        format_name=context.format_name,
        player_count=context.player_count,
        category=context.category,
        description=context.description,
        is_system_preset=context.is_system_preset,
        frozen_at=None,
        frozen_by_user_id=None,
        roles=[
            GameFormatContextRoleRead(
                id=None,
                source_format_role_id=role.id,
                role_name=role.role_name,
                faction=role.faction,
                role_count=role.role_count,
                display_order=role.display_order,
                metadata_json=deepcopy(role.metadata_json),
            )
            for role in context.format_roles
        ],
    )


def get_game_format_context_or_404(db: Session, game_id: int) -> Game:
    """Load one game with both live and frozen format relationships."""

    statement = (
        select(Game)
        .options(
            selectinload(Game.format).selectinload(GameFormat.format_roles),
            *FORMAT_SNAPSHOT_LOAD_OPTIONS,
        )
        .where(Game.id == game_id)
    )
    game = db.scalar(statement)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found.")
    return game
