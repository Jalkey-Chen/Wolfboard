from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Role(Base):
    """System permission role assigned through the user-role mapping table."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    role_key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    role_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)

    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
