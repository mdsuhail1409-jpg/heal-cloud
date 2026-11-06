"""
Incident, IncidentEvent, and Diagnosis Models for HealCloud
"""

import enum
import uuid
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Float,
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
    from app.models.user import User


class IncidentSeverityEnum(str, enum.Enum):
    P1_CRITICAL = "P1_CRITICAL"
    P2_HIGH = "P2_HIGH"
    P3_MEDIUM = "P3_MEDIUM"
    P4_LOW = "P4_LOW"


class IncidentStatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    RECOVERY_PENDING = "RECOVERY_PENDING"
    RECOVERING = "RECOVERING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    FAILED = "FAILED"


class IncidentEventTypeEnum(str, enum.Enum):
    DETECTED = "DETECTED"
    DIAGNOSED = "DIAGNOSED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ASSIGNED = "ASSIGNED"
    STATUS_CHANGED = "STATUS_CHANGED"
    THRESHOLD_BREACHED = "THRESHOLD_BREACHED"
    RECOVERY_REQUESTED = "RECOVERY_REQUESTED"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    RECOVERY_VERIFIED = "RECOVERY_VERIFIED"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    RESOLVED = "RESOLVED"
    NOTE_ADDED = "NOTE_ADDED"


class Incident(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "incidents"

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
    service_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_number: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(
        String(50),
        default=IncidentSeverityEnum.P2_HIGH.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=IncidentStatusEnum.OPEN.value,
        nullable=False,
        index=True,
    )
    assigned_to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    service: Mapped["Service"] = relationship("Service", backref="incidents")
    assigned_to: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_to_user_id],
    )
    events: Mapped[List["IncidentEvent"]] = relationship(
        "IncidentEvent",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentEvent.created_at.asc()",
    )
    diagnoses: Mapped[List["Diagnosis"]] = relationship(
        "Diagnosis",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="Diagnosis.created_at.asc()",
    )


class IncidentEvent(Base, UUIDMixin):
    __tablename__ = "incident_events"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    incident: Mapped["Incident"] = relationship("Incident", back_populates="events")


class Diagnosis(Base, UUIDMixin):
    __tablename__ = "diagnoses"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    root_cause_hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    recommended_action: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    incident: Mapped["Incident"] = relationship("Incident", back_populates="diagnoses")
