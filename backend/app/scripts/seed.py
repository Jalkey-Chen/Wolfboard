"""Seed default roles and local development users."""

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.role import Role
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


def main() -> None:
    """Seed default roles and sample users for local development."""

    roles_by_key = seed_roles()
    seed_users(roles_by_key)
    print("Seed data created or already up to date.")


if __name__ == "__main__":
    main()
