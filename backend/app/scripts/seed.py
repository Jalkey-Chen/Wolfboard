"""Seed default roles, users, seasons, event days, registrations, and games.

The seed remains idempotent so local Docker startup can safely re-run it every
time the backend container starts.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.enums import (
    CheckInStatus,
    EventDayCategory,
    EventDayStatus,
    FormatCategory,
    FormatRoleFaction,
    GamePlayerFaction,
    GamePlayerFinalStatus,
    GameStatus,
    GameType,
    RegistrationStatus,
    RegistrationType,
    ScoreAdjustmentType,
    SeasonStatus,
)
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.event_day import EventDay
from app.models.format_role import FormatRole
from app.models.game import Game
from app.models.game_format import GameFormat
from app.models.game_participant import GameParticipant
from app.models.game_player import GamePlayer
from app.models.registration import Registration
from app.models.role import Role
from app.models.season import Season
from app.models.score_adjustment import ScoreAdjustment
from app.models.user import User
from app.models.user_role import UserRole


ROLE_SEED = [
    {
        "role_key": "admin",
        "role_name": "Administrator",
        "description": "Full tournament management access.",
    },
    {
        "role_key": "judge",
        "role_name": "Judge",
        "description": "Can enter and submit owned game results.",
    },
    {
        "role_key": "player",
        "role_name": "Player",
        "description": "Can sign up and view approved information.",
    },
]

USER_SEED = [
    {
        "username": "admin_user",
        "display_name": "管理员示例账号",
        "email": "admin@example.com",
        "roles": ["admin", "judge", "player"],
    },
    {
        "username": "judge_user",
        "display_name": "主持人示例账号",
        "email": "judge@example.com",
        "roles": ["judge", "player"],
    },
    {
        "username": "player_user",
        "display_name": "玩家示例账号",
        "email": "player@example.com",
        "roles": ["player"],
    },
] + [
    {
        "username": f"sample_player_{index:02d}",
        "display_name": f"示例玩家{index:02d}",
        "email": f"sample_player_{index:02d}@example.com",
        "roles": ["player"],
    }
    for index in range(1, 11)
]

DEFAULT_PASSWORD = "password123"
SEASON_NAME = "S1 试验赛季"
LEGACY_SEASON_NAMES = ("S1 Trial Season",)
OPEN_EVENT_DAY_TITLE = "2026-04-05 正赛日"
CLOSED_EVENT_DAY_TITLE = "2026-03-29 社群比赛日"
LEGACY_OPEN_EVENT_DAY_TITLES = ("2026-04-05 Official Match Day",)
LEGACY_CLOSED_EVENT_DAY_TITLES = ("2026-03-29 Community Match Day",)
SEEDED_GAME_NOTE_PREFIX = "Milestone 3 示例对局"
SEEDED_RESULT_ADJUSTMENT_REASON = "Milestone 6 stable-participant sample"

PRESET_FORMATS = [
    {
        "format_name": "预女猎白混",
        "format_key": "yu-nv-lie-bai-hun",
        "player_count": 12,
        "category": FormatCategory.STANDARD,
        "description": "Standard twelve-player format with prophet, witch, hunter, idiot, and mixed blood.",
        "roles": [
            {"role_name": "预言家", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["check"]}},
            {"role_name": "女巫", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["save", "poison"]}},
            {"role_name": "猎人", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["death_trigger"]}},
            {"role_name": "白痴", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"can_be_elected_sheriff": True}},
            {"role_name": "混血儿", "faction": FormatRoleFaction.THIRD_PARTY, "role_count": 1, "metadata_json": {"skill_tags": ["inherit"]}},
            {"role_name": "平民", "faction": FormatRoleFaction.GOOD, "role_count": 3, "metadata_json": None},
            {"role_name": "狼人", "faction": FormatRoleFaction.WOLF, "role_count": 3, "metadata_json": None},
            {"role_name": "白狼王", "faction": FormatRoleFaction.WOLF, "role_count": 1, "metadata_json": {"skill_tags": ["self_explode"]}},
        ],
    },
    {
        "format_name": "狼王守卫",
        "format_key": "wolf-king-guard",
        "player_count": 12,
        "category": FormatCategory.STANDARD,
        "description": "Classic wolf-king plus guard configuration for official play.",
        "roles": [
            {"role_name": "预言家", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["check"]}},
            {"role_name": "女巫", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["save", "poison"]}},
            {"role_name": "猎人", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["death_trigger"]}},
            {"role_name": "守卫", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["protect"]}},
            {"role_name": "平民", "faction": FormatRoleFaction.GOOD, "role_count": 4, "metadata_json": None},
            {"role_name": "狼人", "faction": FormatRoleFaction.WOLF, "role_count": 3, "metadata_json": None},
            {"role_name": "狼王", "faction": FormatRoleFaction.WOLF, "role_count": 1, "metadata_json": {"skill_tags": ["death_trigger"]}},
        ],
    },
    {
        "format_name": "狼美骑士",
        "format_key": "wolf-beauty-knight",
        "player_count": 12,
        "category": FormatCategory.SPECIAL,
        "description": "Wolf beauty and knight variation with sharper daytime pressure.",
        "roles": [
            {"role_name": "预言家", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["check"]}},
            {"role_name": "女巫", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["save", "poison"]}},
            {"role_name": "骑士", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["challenge"]}},
            {"role_name": "白痴", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": None},
            {"role_name": "平民", "faction": FormatRoleFaction.GOOD, "role_count": 4, "metadata_json": None},
            {"role_name": "狼人", "faction": FormatRoleFaction.WOLF, "role_count": 3, "metadata_json": None},
            {"role_name": "狼美人", "faction": FormatRoleFaction.WOLF, "role_count": 1, "metadata_json": {"skill_tags": ["charm"]}},
        ],
    },
    {
        "format_name": "机械狼通灵师",
        "format_key": "mecha-wolf-medium",
        "player_count": 12,
        "category": FormatCategory.SPECIAL,
        "description": "Mechanical wolf paired with medium for a higher-information lineup.",
        "roles": [
            {"role_name": "预言家", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["check"]}},
            {"role_name": "女巫", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["save", "poison"]}},
            {"role_name": "通灵师", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["reveal"]}},
            {"role_name": "猎人", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["death_trigger"]}},
            {"role_name": "平民", "faction": FormatRoleFaction.GOOD, "role_count": 4, "metadata_json": None},
            {"role_name": "狼人", "faction": FormatRoleFaction.WOLF, "role_count": 3, "metadata_json": None},
            {"role_name": "机械狼", "faction": FormatRoleFaction.WOLF, "role_count": 1, "metadata_json": {"skill_tags": ["copy_skill"]}},
        ],
    },
    {
        "format_name": "梦魇摄梦人",
        "format_key": "nightmare-dreamweaver",
        "player_count": 12,
        "category": FormatCategory.SPECIAL,
        "description": "Nightmare and dreamweaver variant with layered night actions.",
        "roles": [
            {"role_name": "预言家", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["check"]}},
            {"role_name": "女巫", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["save", "poison"]}},
            {"role_name": "摄梦人", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["sleep"]}},
            {"role_name": "猎人", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["death_trigger"]}},
            {"role_name": "平民", "faction": FormatRoleFaction.GOOD, "role_count": 4, "metadata_json": None},
            {"role_name": "狼人", "faction": FormatRoleFaction.WOLF, "role_count": 3, "metadata_json": None},
            {"role_name": "梦魇", "faction": FormatRoleFaction.WOLF, "role_count": 1, "metadata_json": {"skill_tags": ["silence"]}},
        ],
    },
    {
        "format_name": "孤注一掷",
        "format_key": "all-in",
        "player_count": 12,
        "category": FormatCategory.FUN,
        "description": "High-variance fun format with swingier role distribution.",
        "roles": [
            {"role_name": "预言家", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["check"]}},
            {"role_name": "女巫", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["save", "poison"]}},
            {"role_name": "守卫", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["protect"]}},
            {"role_name": "禁言长老", "faction": FormatRoleFaction.SPECIAL, "role_count": 1, "metadata_json": {"skill_tags": ["silence"]}},
            {"role_name": "平民", "faction": FormatRoleFaction.GOOD, "role_count": 4, "metadata_json": None},
            {"role_name": "狼人", "faction": FormatRoleFaction.WOLF, "role_count": 2, "metadata_json": None},
            {"role_name": "狼王", "faction": FormatRoleFaction.WOLF, "role_count": 1, "metadata_json": {"skill_tags": ["death_trigger"]}},
            {"role_name": "石像鬼", "faction": FormatRoleFaction.WOLF, "role_count": 1, "metadata_json": {"skill_tags": ["check"]}},
        ],
    },
    {
        "format_name": "盗宝大师",
        "format_key": "treasure-raider-master",
        "player_count": 12,
        "category": FormatCategory.SPECIAL,
        "description": "Treasure-raider master format with loot-centric special role pressure.",
        "roles": [
            {"role_name": "预言家", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["check"]}},
            {"role_name": "女巫", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["save", "poison"]}},
            {"role_name": "盗宝大师", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["steal"]}},
            {"role_name": "猎人", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["death_trigger"]}},
            {"role_name": "平民", "faction": FormatRoleFaction.GOOD, "role_count": 4, "metadata_json": None},
            {"role_name": "狼人", "faction": FormatRoleFaction.WOLF, "role_count": 3, "metadata_json": None},
            {"role_name": "狼王", "faction": FormatRoleFaction.WOLF, "role_count": 1, "metadata_json": {"skill_tags": ["death_trigger"]}},
        ],
    },
    {
        "format_name": "假面舞会",
        "format_key": "masquerade-ball",
        "player_count": 12,
        "category": FormatCategory.FUN,
        "description": "Masquerade variant designed for event-day side tables and fun games.",
        "roles": [
            {"role_name": "预言家", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["check"]}},
            {"role_name": "女巫", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["save", "poison"]}},
            {"role_name": "舞者", "faction": FormatRoleFaction.SPECIAL, "role_count": 1, "metadata_json": {"skill_tags": ["swap"]}},
            {"role_name": "猎人", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["death_trigger"]}},
            {"role_name": "平民", "faction": FormatRoleFaction.GOOD, "role_count": 4, "metadata_json": None},
            {"role_name": "狼人", "faction": FormatRoleFaction.WOLF, "role_count": 3, "metadata_json": None},
            {"role_name": "狼美人", "faction": FormatRoleFaction.WOLF, "role_count": 1, "metadata_json": {"skill_tags": ["charm"]}},
        ],
    },
    {
        "format_name": "唯邻是从",
        "format_key": "follow-the-neighbor",
        "player_count": 12,
        "category": FormatCategory.FUN,
        "description": "Neighbor-driven variant that adds adjacency pressure to decisions.",
        "roles": [
            {"role_name": "预言家", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["check"]}},
            {"role_name": "女巫", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["save", "poison"]}},
            {"role_name": "守卫", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["protect"]}},
            {"role_name": "邻长", "faction": FormatRoleFaction.SPECIAL, "role_count": 1, "metadata_json": {"skill_tags": ["adjacency"]}},
            {"role_name": "平民", "faction": FormatRoleFaction.GOOD, "role_count": 4, "metadata_json": None},
            {"role_name": "狼人", "faction": FormatRoleFaction.WOLF, "role_count": 3, "metadata_json": None},
            {"role_name": "狼王", "faction": FormatRoleFaction.WOLF, "role_count": 1, "metadata_json": {"skill_tags": ["death_trigger"]}},
        ],
    },
    {
        "format_name": "魔幻对决",
        "format_key": "magic-duel",
        "player_count": 12,
        "category": FormatCategory.SPECIAL,
        "description": "Fantasy duel format with mirror-like pressure on both factions.",
        "roles": [
            {"role_name": "预言家", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["check"]}},
            {"role_name": "女巫", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["save", "poison"]}},
            {"role_name": "通灵师", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["reveal"]}},
            {"role_name": "骑士", "faction": FormatRoleFaction.GOOD, "role_count": 1, "metadata_json": {"skill_tags": ["challenge"]}},
            {"role_name": "平民", "faction": FormatRoleFaction.GOOD, "role_count": 4, "metadata_json": None},
            {"role_name": "狼人", "faction": FormatRoleFaction.WOLF, "role_count": 2, "metadata_json": None},
            {"role_name": "石像鬼", "faction": FormatRoleFaction.WOLF, "role_count": 1, "metadata_json": {"skill_tags": ["check"]}},
            {"role_name": "狼美人", "faction": FormatRoleFaction.WOLF, "role_count": 1, "metadata_json": {"skill_tags": ["charm"]}},
        ],
    },
]


def seed_roles() -> dict[str, Role]:
    """Create the default system roles if they do not already exist.

    The seed script is idempotent so container startup can safely re-run it on
    every boot without creating duplicate rows.
    """

    with SessionLocal() as db:
        existing_roles = {
            role.role_key: role
            for role in db.scalars(select(Role)).all()
        }

        for role_payload in ROLE_SEED:
            if role_payload["role_key"] not in existing_roles:
                role = Role(**role_payload)
                db.add(role)
                existing_roles[role.role_key] = role

        db.commit()

        return {
            role.role_key: role
            for role in db.scalars(select(Role)).all()
        }


def seed_users(roles_by_key: dict[str, Role]) -> None:
    """Create sample users and attach the requested role mappings.

    Users are created first, then linked through the normalized `user_roles`
    table so the seed data matches the intended production schema.
    """

    with SessionLocal() as db:
        existing_users = {
            user.username: user
            for user in db.scalars(select(User)).all()
        }

        for user_payload in USER_SEED:
            user = existing_users.get(user_payload["username"])
            if user is None:
                user = User(
                    username=user_payload["username"],
                    display_name=user_payload["display_name"],
                    email=user_payload["email"],
                    password_hash=get_password_hash(DEFAULT_PASSWORD),
                    account_status="active",
                )
                db.add(user)
                db.flush()
            else:
                user.display_name = user_payload["display_name"]
                user.email = user_payload["email"]

            existing_role_ids = {
                user_role.role_id
                for user_role in db.scalars(
                    select(UserRole).where(UserRole.user_id == user.id)
                ).all()
            }

            for role_key in user_payload["roles"]:
                role = roles_by_key[role_key]
                if role.id not in existing_role_ids:
                    # Only create missing mappings so repeated seeds remain safe.
                    db.add(UserRole(user_id=user.id, role_id=role.id))

        db.commit()


def seed_seasons_and_event_days() -> None:
    """Create Milestone 2 sample season and event-day records.

    The seeded data intentionally includes one open event day and one closed
    event day so both player registration and admin check-in flows can be
    tested immediately after startup.
    """

    with SessionLocal() as db:
        admin_user = db.scalar(select(User).where(User.username == "admin_user"))
        if admin_user is None:
            raise RuntimeError("The admin_user seed must exist before seeding seasons.")

        matching_seasons = db.scalars(
            select(Season).where(Season.name.in_((SEASON_NAME, *LEGACY_SEASON_NAMES)))
        ).all()
        sorted_matching_seasons = sorted(matching_seasons, key=lambda row: row.id)
        season = sorted_matching_seasons[0] if sorted_matching_seasons else None
        if season is None:
            season = Season(
                name=SEASON_NAME,
                description="用于本地开发的示例赛季数据。",
                start_date=date(2026, 3, 1),
                end_date=date(2026, 5, 31),
                status=SeasonStatus.ACTIVE,
                created_by=admin_user.id,
            )
            db.add(season)
            db.flush()
        else:
            season.name = SEASON_NAME
            season.description = "用于本地开发的示例赛季数据。"
            season.start_date = date(2026, 3, 1)
            season.end_date = date(2026, 5, 31)
            season.status = SeasonStatus.ACTIVE

        def delete_duplicate_event_day(event_day: EventDay) -> None:
            for registration in db.scalars(
                select(Registration).where(Registration.event_day_id == event_day.id)
            ).all():
                db.delete(registration)
            for game in db.scalars(select(Game).where(Game.event_day_id == event_day.id)).all():
                db.delete(game)
            db.delete(event_day)

        open_candidates = db.scalars(
            select(EventDay).where(
                EventDay.season_id.in_([row.id for row in matching_seasons] or [season.id]),
                EventDay.title.in_((OPEN_EVENT_DAY_TITLE, *LEGACY_OPEN_EVENT_DAY_TITLES)),
            )
        ).all()
        open_candidates = sorted(open_candidates, key=lambda row: row.id)
        open_event_day = open_candidates[0] if open_candidates else None
        if open_event_day is None:
            open_event_day = EventDay(
                season_id=season.id,
                title=OPEN_EVENT_DAY_TITLE,
                event_date=date(2026, 4, 5),
                venue="风城俱乐部",
                category=EventDayCategory.OFFICIAL,
                notes="用于演示开放报名流程的示例比赛日。",
                registration_open_at=datetime.now() - timedelta(days=2),
                registration_close_at=datetime.now() + timedelta(days=5),
                status=EventDayStatus.OPEN_FOR_REGISTRATION,
                created_by=admin_user.id,
            )
            db.add(open_event_day)
        else:
            open_event_day.season_id = season.id
            open_event_day.title = OPEN_EVENT_DAY_TITLE
            open_event_day.event_date = date(2026, 4, 5)
            open_event_day.venue = "风城俱乐部"
            open_event_day.category = EventDayCategory.OFFICIAL
            open_event_day.notes = "用于演示开放报名流程的示例比赛日。"
            open_event_day.registration_open_at = datetime.now() - timedelta(days=2)
            open_event_day.registration_close_at = datetime.now() + timedelta(days=5)
            open_event_day.status = EventDayStatus.OPEN_FOR_REGISTRATION

        for duplicate_event_day in open_candidates[1:]:
            delete_duplicate_event_day(duplicate_event_day)

        closed_candidates = db.scalars(
            select(EventDay).where(
                EventDay.season_id.in_([row.id for row in matching_seasons] or [season.id]),
                EventDay.title.in_((CLOSED_EVENT_DAY_TITLE, *LEGACY_CLOSED_EVENT_DAY_TITLES)),
            )
        ).all()
        closed_candidates = sorted(closed_candidates, key=lambda row: row.id)
        closed_event_day = closed_candidates[0] if closed_candidates else None
        if closed_event_day is None:
            closed_event_day = EventDay(
                season_id=season.id,
                title=CLOSED_EVENT_DAY_TITLE,
                event_date=date(2026, 3, 29),
                venue="市中心赛事馆",
                category=EventDayCategory.MIXED,
                notes="用于演示报名关闭与签到管理的示例比赛日。",
                registration_open_at=datetime(2026, 3, 20, 12, 0, 0),
                registration_close_at=datetime(2026, 3, 27, 23, 0, 0),
                status=EventDayStatus.REGISTRATION_CLOSED,
                created_by=admin_user.id,
            )
            db.add(closed_event_day)
        else:
            closed_event_day.season_id = season.id
            closed_event_day.title = CLOSED_EVENT_DAY_TITLE
            closed_event_day.event_date = date(2026, 3, 29)
            closed_event_day.venue = "市中心赛事馆"
            closed_event_day.category = EventDayCategory.MIXED
            closed_event_day.notes = "用于演示报名关闭与签到管理的示例比赛日。"
            closed_event_day.registration_open_at = datetime(2026, 3, 20, 12, 0, 0)
            closed_event_day.registration_close_at = datetime(2026, 3, 27, 23, 0, 0)
            closed_event_day.status = EventDayStatus.REGISTRATION_CLOSED

        for duplicate_event_day in closed_candidates[1:]:
            delete_duplicate_event_day(duplicate_event_day)

        for duplicate_season in sorted_matching_seasons[1:]:
            db.delete(duplicate_season)

        db.commit()


def seed_registrations() -> None:
    """Create sample registrations used to test signup and admin check-in flows.

    The open event day now includes enough registered users to support Milestone
    4 result-entry testing against a 12-player format.
    """

    with SessionLocal() as db:
        users_by_username = {
            user.username: user
            for user in db.scalars(select(User)).all()
        }
        event_days_by_title = {
            event_day.title: event_day
            for event_day in db.scalars(select(EventDay)).all()
        }

        registration_seed = [
            {
                "event_title": OPEN_EVENT_DAY_TITLE,
                "username": "judge_user",
                "registration_status": RegistrationStatus.WAITLISTED,
                "check_in_status": CheckInStatus.NOT_CHECKED_IN,
                "registration_type": RegistrationType.SUBSTITUTE,
                "note": "Waitlist sample.",
            },
            {
                "event_title": OPEN_EVENT_DAY_TITLE,
                "username": "admin_user",
                "registration_status": RegistrationStatus.REGISTERED,
                "check_in_status": CheckInStatus.CHECKED_IN,
                "registration_type": RegistrationType.GUEST,
                "note": "Admin registered as a sample player option.",
            },
            {
                "event_title": OPEN_EVENT_DAY_TITLE,
                "username": "player_user",
                "registration_status": RegistrationStatus.REGISTERED,
                "check_in_status": CheckInStatus.CHECKED_IN,
                "registration_type": RegistrationType.MAIN,
                "note": "Primary sample player.",
            },
            {
                "event_title": CLOSED_EVENT_DAY_TITLE,
                "username": "admin_user",
                "registration_status": RegistrationStatus.REGISTERED,
                "check_in_status": CheckInStatus.CHECKED_IN,
                "registration_type": RegistrationType.GUEST,
                "note": "Checked-in sample.",
            },
            {
                "event_title": CLOSED_EVENT_DAY_TITLE,
                "username": "player_user",
                "registration_status": RegistrationStatus.REGISTERED,
                "check_in_status": CheckInStatus.ABSENT,
                "registration_type": RegistrationType.MAIN,
                "note": "Absent sample.",
            },
        ] + [
            {
                "event_title": OPEN_EVENT_DAY_TITLE,
                "username": f"sample_player_{index:02d}",
                "registration_status": RegistrationStatus.REGISTERED,
                "check_in_status": CheckInStatus.CHECKED_IN,
                "registration_type": RegistrationType.MAIN,
                "note": "Seeded open-event player for result-entry testing.",
            }
            for index in range(1, 11)
        ]
        desired_pairs = {
            (event_days_by_title[payload["event_title"]].id, users_by_username[payload["username"]].id)
            for payload in registration_seed
        }

        sample_event_day_ids = {
            event_days_by_title[OPEN_EVENT_DAY_TITLE].id,
            event_days_by_title[CLOSED_EVENT_DAY_TITLE].id,
        }
        sample_user_ids = {
            users_by_username["admin_user"].id,
            users_by_username["judge_user"].id,
            users_by_username["player_user"].id,
        } | {
            users_by_username[f"sample_player_{index:02d}"].id
            for index in range(1, 11)
        }

        stale_registrations = db.scalars(
            select(Registration).where(
                Registration.event_day_id.in_(sample_event_day_ids),
                Registration.user_id.in_(sample_user_ids),
            )
        ).all()
        for registration in stale_registrations:
            if (registration.event_day_id, registration.user_id) not in desired_pairs:
                db.delete(registration)

        for registration_payload in registration_seed:
            user = users_by_username[registration_payload["username"]]
            event_day = event_days_by_title[registration_payload["event_title"]]

            registration = db.scalar(
                select(Registration).where(
                    Registration.event_day_id == event_day.id,
                    Registration.user_id == user.id,
                )
            )

            if registration is None:
                registration = Registration(
                    event_day_id=event_day.id,
                    user_id=user.id,
                )
                db.add(registration)

            registration.registration_status = registration_payload["registration_status"]
            registration.check_in_status = registration_payload["check_in_status"]
            registration.registration_type = registration_payload["registration_type"]
            registration.note = registration_payload["note"]

        db.commit()


def seed_formats() -> None:
    """Create or update the preset game formats and their role compositions."""

    with SessionLocal() as db:
        existing_formats = {
            game_format.format_key: game_format
            for game_format in db.scalars(select(GameFormat)).all()
        }

        for format_payload in PRESET_FORMATS:
            game_format = existing_formats.get(format_payload["format_key"])
            if game_format is None:
                game_format = GameFormat(
                    format_name=format_payload["format_name"],
                    format_key=format_payload["format_key"],
                    player_count=format_payload["player_count"],
                    category=format_payload["category"],
                    description=format_payload["description"],
                    is_active=True,
                    is_system_preset=True,
                )
                db.add(game_format)
                db.flush()
            else:
                game_format.format_name = format_payload["format_name"]
                game_format.player_count = format_payload["player_count"]
                game_format.category = format_payload["category"]
                game_format.description = format_payload["description"]
                game_format.is_active = True
                game_format.is_system_preset = True
                db.flush()
                db.query(FormatRole).filter(FormatRole.format_id == game_format.id).delete()

            for display_order, role_payload in enumerate(format_payload["roles"], start=1):
                db.add(
                    FormatRole(
                        format_id=game_format.id,
                        role_name=role_payload["role_name"],
                        faction=role_payload["faction"],
                        role_count=role_payload["role_count"],
                        display_order=display_order,
                        metadata_json=role_payload["metadata_json"],
                    )
                )

        db.commit()


def seed_games() -> None:
    """Create sample games for the seeded event days.

    The sample rows give Milestone 3 pages immediate data for format browsing,
    game management, and judge-owned game lists after startup.
    """

    with SessionLocal() as db:
        users_by_username = {
            user.username: user
            for user in db.scalars(select(User)).all()
        }
        event_days_by_title = {
            event_day.title: event_day
            for event_day in db.scalars(select(EventDay)).all()
        }
        formats_by_key = {
            game_format.format_key: game_format
            for game_format in db.scalars(select(GameFormat)).all()
        }

        game_seed = [
            {
                "event_title": OPEN_EVENT_DAY_TITLE,
                "table_number": 1,
                "game_number": 1,
                "format_key": "wolf-king-guard",
                "judge_username": "judge_user",
                "game_type": GameType.OFFICIAL,
                "status": GameStatus.DRAFT,
                "notes": f"{SEEDED_GAME_NOTE_PREFIX}：正式局第 1 轮。",
            },
            {
                "event_title": OPEN_EVENT_DAY_TITLE,
                "table_number": 1,
                "game_number": 2,
                "format_key": "wolf-beauty-knight",
                "judge_username": "admin_user",
                "game_type": GameType.OFFICIAL,
                "status": GameStatus.DRAFT,
                "notes": f"{SEEDED_GAME_NOTE_PREFIX}：正式局第 2 轮。",
            },
            {
                "event_title": OPEN_EVENT_DAY_TITLE,
                "table_number": 1,
                "game_number": 3,
                "format_key": "mecha-wolf-medium",
                "judge_username": "judge_user",
                "game_type": GameType.OFFICIAL,
                "status": GameStatus.IN_PROGRESS,
                "notes": f"{SEEDED_GAME_NOTE_PREFIX}：正式局第 3 轮。",
            },
            {
                "event_title": CLOSED_EVENT_DAY_TITLE,
                "table_number": 1,
                "game_number": 1,
                "format_key": "masquerade-ball",
                "judge_username": "admin_user",
                "game_type": GameType.FUN,
                "status": GameStatus.CONFIRMED,
                "notes": f"{SEEDED_GAME_NOTE_PREFIX}：娱乐副桌。",
            },
        ]

        desired_pairs = {
            (
                event_days_by_title[payload["event_title"]].id,
                payload["table_number"],
                payload["game_number"],
            )
            for payload in game_seed
        }
        seeded_games = db.scalars(select(Game).where(Game.notes.like(f"{SEEDED_GAME_NOTE_PREFIX}%"))).all()
        for game in seeded_games:
            pair = (game.event_day_id, game.table_number, game.game_number)
            if pair not in desired_pairs:
                db.delete(game)

        for game_payload in game_seed:
            event_day = event_days_by_title[game_payload["event_title"]]
            judge_user = users_by_username[game_payload["judge_username"]]
            game_format = formats_by_key[game_payload["format_key"]]

            game = db.scalar(
                select(Game).where(
                    Game.event_day_id == event_day.id,
                    Game.table_number == game_payload["table_number"],
                    Game.game_number == game_payload["game_number"],
                )
            )

            if game is None:
                game = Game(
                    event_day_id=event_day.id,
                    table_number=game_payload["table_number"],
                    game_number=game_payload["game_number"],
                    format_id=game_format.id,
                    judge_user_id=judge_user.id,
                )
                db.add(game)

            game.format_id = game_format.id
            game.judge_user_id = judge_user.id
            game.game_type = game_payload["game_type"]
            game.status = game_payload["status"]
            game.notes = game_payload["notes"]
            if game.status == GameStatus.CONFIRMED:
                game.started_at = datetime(2026, 3, 29, 13, 0, tzinfo=timezone.utc)
                game.ended_at = datetime(2026, 3, 29, 14, 30, tzinfo=timezone.utc)
            elif game.status == GameStatus.IN_PROGRESS:
                game.started_at = datetime(2026, 4, 5, 13, 0, tzinfo=timezone.utc)
                game.ended_at = None
            else:
                game.started_at = None
                game.ended_at = None

        db.flush()
        sample_game = db.scalar(
            select(Game).where(
                Game.notes == f"{SEEDED_GAME_NOTE_PREFIX}：正式局第 3 轮。",
            )
        )
        if sample_game is not None:
            sample_rows = [
                ("sample_player_01", 1, "预言家", GamePlayerFaction.GOOD, True),
                ("sample_player_02", 2, "狼人", GamePlayerFaction.WOLF, False),
            ]
            for username, seat_number, role_name, faction, is_winner in sample_rows:
                user = users_by_username[username]
                participant = db.scalar(
                    select(GameParticipant).where(
                        GameParticipant.game_id == sample_game.id,
                        GameParticipant.user_id == user.id,
                    )
                )
                if participant is None:
                    occupied_seat = db.scalar(
                        select(GameParticipant).where(
                            GameParticipant.game_id == sample_game.id,
                            GameParticipant.seat_number == seat_number,
                        )
                    )
                    if occupied_seat is not None:
                        continue
                    participant = GameParticipant(
                        game_id=sample_game.id,
                        user_id=user.id,
                        seat_number=seat_number,
                        display_name_snapshot=user.display_name,
                    )
                    db.add(participant)
                    db.flush()

                game_player = db.scalar(
                    select(GamePlayer).where(GamePlayer.participant_id == participant.id)
                )
                if game_player is None:
                    game_player = GamePlayer(
                        game_id=sample_game.id,
                        participant_id=participant.id,
                        role_name=role_name,
                        faction=faction,
                        final_status=GamePlayerFinalStatus.ALIVE,
                        is_winner=is_winner,
                        base_score=1.0 if is_winner else 0.0,
                        adjustment_score=0.0,
                        final_score=1.0 if is_winner else 0.0,
                        remarks="Stable participant seed sample",
                    )
                    db.add(game_player)
                    db.flush()

                if seat_number == 1:
                    adjustment = db.scalar(
                        select(ScoreAdjustment).where(
                            ScoreAdjustment.game_player_id == game_player.id,
                            ScoreAdjustment.reason == SEEDED_RESULT_ADJUSTMENT_REASON,
                        )
                    )
                    if adjustment is None:
                        db.add(
                            ScoreAdjustment(
                                game_player_id=game_player.id,
                                adjustment_type=ScoreAdjustmentType.JUDGE_BONUS,
                                delta=0.25,
                                reason=SEEDED_RESULT_ADJUSTMENT_REASON,
                                created_by=sample_game.judge_user_id,
                            )
                        )
                        game_player.adjustment_score = 0.25
                        game_player.final_score = game_player.base_score + 0.25

        db.commit()


def main() -> None:
    """Seed default roles and sample milestone data for local development."""

    roles_by_key = seed_roles()
    seed_users(roles_by_key)
    seed_seasons_and_event_days()
    seed_registrations()
    seed_formats()
    seed_games()
    print("Seed data created or already up to date.")


if __name__ == "__main__":
    main()
