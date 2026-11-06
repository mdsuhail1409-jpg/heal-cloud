"""
Organization and Workspace SQLAlchemy Models
"""

from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin, GUID

if TYPE_CHECKING:
    from app.models.membership import Membership


class Organization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    memberships: Mapped[List["Membership"]] = relationship(
        "Membership",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    workspaces: Mapped[List["Workspace"]] = relationship(
        "Workspace",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, slug='{self.slug}')>"


class Workspace(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workspaces"

    organization_id: Mapped[GUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="workspaces")

    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_organization_workspace_slug"),
    )

    def __repr__(self) -> str:
        return f"<Workspace(id={self.id}, org_id={self.organization_id}, slug='{self.slug}')>"

