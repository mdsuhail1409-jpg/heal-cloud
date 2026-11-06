"""
Membership SQLAlchemy Model and Role Definitions
"""

import enum
from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, GUID

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class RoleEnum(str, enum.Enum):
    ORG_OWNER = "ORG_OWNER"
    ORG_ADMIN = "ORG_ADMIN"
    RELIABILITY_ENGINEER = "RELIABILITY_ENGINEER"
    VIEWER = "VIEWER"

    @classmethod
    def hierarchy(cls) -> dict:
        return {
            cls.ORG_OWNER: 40,
            cls.ORG_ADMIN: 30,
            cls.RELIABILITY_ENGINEER: 20,
            cls.VIEWER: 10,
        }

    def has_permission(self, required_role: "RoleEnum") -> bool:
        """Check whether current role satisfies or exceeds the required role."""
        weights = self.hierarchy()
        return weights.get(self, 0) >= weights.get(required_role, 0)


class Membership(Base, UUIDMixin):
    __tablename__ = "memberships"

    organization_id: Mapped[GUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[GUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        default=RoleEnum.VIEWER.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="memberships")
    user: Mapped["User"] = relationship("User", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_user_membership"),
    )

    def __repr__(self) -> str:
        return f"<Membership(org_id={self.organization_id}, user_id={self.user_id}, role='{self.role}')>"
