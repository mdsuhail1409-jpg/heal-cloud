"""
Recovery Policies, Executions, and Approval Requests Models for HealCloud
"""

import enum
import uuid
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin, GUID

if TYPE_CHECKING:
    from app.models.organization import Organization, Workspace
    from app.models.service import Service
    from app.models.incident import Incident
    from app.models.user import User


class AllowlistedActionEnum(str, enum.Enum):
    SIMULATE_RESTART = "SIMULATE_RESTART"
    SIMULATE_SCALE_UP = "SIMULATE_SCALE_UP"
    SIMULATE_CIRCUIT_BREAK = "SIMULATE_CIRCUIT_BREAK"
    SIMULATE_FLUSH_CACHE = "SIMULATE_FLUSH_CACHE"


class RecoveryStatusEnum(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class ApprovalDecisionEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RiskTierEnum(str, enum.Enum):
    TIER_1_LOW = "TIER_1_LOW"
    TIER_2_MEDIUM = "TIER_2_MEDIUM"
    TIER_3_HIGH = "TIER_3_HIGH"


class RecoveryPolicy(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "recovery_policies"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_condition: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(
        String(100),
        default=AllowlistedActionEnum.SIMULATE_RESTART.value,
        nullable=False,
    )
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    service: Mapped[Optional["Service"]] = relationship("Service", backref="recovery_policies")


class RecoveryExecution(Base, UUIDMixin):
    __tablename__ = "recovery_executions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("recovery_policies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_taken: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default=RecoveryStatusEnum.QUEUED.value,
        nullable=False,
        index=True,
    )
    execution_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    verification_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requested_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", backref="recovery_executions")
    policy: Mapped[Optional["RecoveryPolicy"]] = relationship("RecoveryPolicy", backref="executions")
    service: Mapped["Service"] = relationship("Service")
    requested_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[requested_by_user_id])


class ApprovalRequest(Base, UUIDMixin):
    __tablename__ = "approval_requests"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("recovery_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proposed_action: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_tier: Mapped[str] = mapped_column(
        String(50),
        default=RiskTierEnum.TIER_2_MEDIUM.value,
        nullable=False,
    )
    blast_radius: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default=ApprovalDecisionEnum.PENDING.value,
        nullable=False,
        index=True,
    )
    decision_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requested_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decided_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident")
    service: Mapped["Service"] = relationship("Service")
    execution: Mapped[Optional["RecoveryExecution"]] = relationship("RecoveryExecution")
    requested_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[requested_by_user_id])
    decided_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[decided_by_user_id])

