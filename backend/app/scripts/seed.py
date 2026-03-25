"""Seed default roles, users, seasons, event days, and registrations.

The seed remains idempotent so local Docker startup can safely re-run it every
time the backend container starts.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.core.enums import CheckInStatus, EventDayCategory, EventDayStatus, RegistrationStatus, RegistrationType, SeasonStatus
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.event_day import EventDay
from app.models.registration import Registration
from app.models.role import Role
from app.models.season import Season
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
        "display_name": "Admin User",
        "email": "admin@example.com",
        "roles": ["admin", "judge", "player"],
    },
    {
        "username": "judge_user",
        "display_name": "Judge User",
        "email": "judge@example.com",
        "roles": ["judge", "player"],
    },
    {
        "username": "player_user",
        "display_name": "Player User",
        "email": "player@example.com",
        "roles": ["player"],
    },
]

DEFAULT_PASSWORD = "password123"
SEASON_NAME = "S1 Trial Season"
OPEN_EVENT_DAY_TITLE = "2026-04-05 Official Match Day"
CLOSED_EVENT_DAY_TITLE = "2026-03-29 Community Match Day"


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

        season = db.scalar(select(Season).where(Season.name == SEASON_NAME))
        if season is None:
            season = Season(
                name=SEASON_NAME,
                description="Sample season seeded for Milestone 2 local development.",
                start_date=date(2026, 3, 1),
                end_date=date(2026, 5, 31),
                status=SeasonStatus.ACTIVE,
                created_by=admin_user.id,
            )
            db.add(season)
            db.flush()
        else:
            season.description = "Sample season seeded for Milestone 2 local development."
            season.start_date = date(2026, 3, 1)
            season.end_date = date(2026, 5, 31)
            season.status = SeasonStatus.ACTIVE

        open_event_day = db.scalar(
            select(EventDay).where(EventDay.season_id == season.id, EventDay.title == OPEN_EVENT_DAY_TITLE)
        )
        if open_event_day is None:
            open_event_day = EventDay(
                season_id=season.id,
                title=OPEN_EVENT_DAY_TITLE,
                event_date=date(2026, 4, 5),
                venue="Windy City Clubhouse",
                category=EventDayCategory.OFFICIAL,
                notes="Open registration sample event day.",
                registration_open_at=datetime.now() - timedelta(days=2),
                registration_close_at=datetime.now() + timedelta(days=5),
                status=EventDayStatus.OPEN_FOR_REGISTRATION,
                created_by=admin_user.id,
            )
            db.add(open_event_day)
        else:
            open_event_day.event_date = date(2026, 4, 5)
            open_event_day.venue = "Windy City Clubhouse"
            open_event_day.category = EventDayCategory.OFFICIAL
            open_event_day.notes = "Open registration sample event day."
            open_event_day.registration_open_at = datetime.now() - timedelta(days=2)
            open_event_day.registration_close_at = datetime.now() + timedelta(days=5)
            open_event_day.status = EventDayStatus.OPEN_FOR_REGISTRATION

        closed_event_day = db.scalar(
            select(EventDay).where(EventDay.season_id == season.id, EventDay.title == CLOSED_EVENT_DAY_TITLE)
        )
        if closed_event_day is None:
            closed_event_day = EventDay(
                season_id=season.id,
                title=CLOSED_EVENT_DAY_TITLE,
                event_date=date(2026, 3, 29),
                venue="Downtown Tournament Hall",
                category=EventDayCategory.MIXED,
                notes="Closed registration sample event day.",
                registration_open_at=datetime(2026, 3, 20, 12, 0, 0),
                registration_close_at=datetime(2026, 3, 27, 23, 0, 0),
                status=EventDayStatus.REGISTRATION_CLOSED,
                created_by=admin_user.id,
            )
            db.add(closed_event_day)
        else:
            closed_event_day.event_date = date(2026, 3, 29)
            closed_event_day.venue = "Downtown Tournament Hall"
            closed_event_day.category = EventDayCategory.MIXED
            closed_event_day.notes = "Closed registration sample event day."
            closed_event_day.registration_open_at = datetime(2026, 3, 20, 12, 0, 0)
            closed_event_day.registration_close_at = datetime(2026, 3, 27, 23, 0, 0)
            closed_event_day.status = EventDayStatus.REGISTRATION_CLOSED

        db.commit()


def seed_registrations() -> None:
    """Create sample registrations used to test signup and admin check-in flows.

    The open event day intentionally leaves `player_user` unregistered so the
    player validation path can exercise a real signup from the UI or API.
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


def main() -> None:
    """Seed default roles and sample users for local development."""

    roles_by_key = seed_roles()
    seed_users(roles_by_key)
    seed_seasons_and_event_days()
    seed_registrations()
    print("Seed data created or already up to date.")


if __name__ == "__main__":
    main()
