"""
Service Inventory, Endpoints, Monitoring Checks and Metric Samples Models
"""

import enum
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    JSON,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin, GUID

if TYPE_CHECKING:
    from app.models.organization import Organization, Workspace


class HealthStatusEnum(str, enum.Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class Service(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "services"

    organization_id: Mapped[GUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[GUID] = mapped_column(
        GUID(),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    health_status: Mapped[str] = mapped_column(
        String(50),
        default=HealthStatusEnum.UNKNOWN.value,
        nullable=False,
        index=True,
    )
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    endpoints: Mapped[List["ServiceEndpoint"]] = relationship(
        "ServiceEndpoint",
        back_populates="service",
        cascade="all, delete-orphan",
    )
    checks: Mapped[List["MonitoringCheck"]] = relationship(
        "MonitoringCheck",
        back_populates="service",
        cascade="all, delete-orphan",
    )
    samples: Mapped[List["MetricSample"]] = relationship(
        "MetricSample",
        back_populates="service",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_workspace_service_name"),
    )

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, name='{self.name}', status='{self.health_status}')>"


class ServiceEndpoint(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "service_endpoints"

    service_id: Mapped[GUID] = mapped_column(
        GUID(),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    method: Mapped[str] = mapped_column(String(10), default="GET", nullable=False)
    expected_status_code: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    timeout_ms: Mapped[int] = mapped_column(Integer, default=5000, nullable=False)
    headers: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    service: Mapped["Service"] = relationship("Service", back_populates="endpoints")
    checks: Mapped[List["MonitoringCheck"]] = relationship(
        "MonitoringCheck",
        back_populates="endpoint",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ServiceEndpoint(id={self.id}, service_id={self.service_id}, url='{self.url}')>"


class MonitoringCheck(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "monitoring_checks"

    service_id: Mapped[GUID] = mapped_column(
        GUID(),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint_id: Mapped[GUID] = mapped_column(
        GUID(),
        ForeignKey("service_endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interval_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    consecutive_failure_threshold: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    service: Mapped["Service"] = relationship("Service", back_populates="checks")
    endpoint: Mapped["ServiceEndpoint"] = relationship("ServiceEndpoint", back_populates="checks")
    samples: Mapped[List["MetricSample"]] = relationship(
        "MetricSample",
        back_populates="check",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<MonitoringCheck(id={self.id}, service_id={self.service_id}, enabled={self.is_enabled})>"


class MetricSample(Base, UUIDMixin):
    __tablename__ = "metric_samples"

    check_id: Mapped[GUID] = mapped_column(
        GUID(),
        ForeignKey("monitoring_checks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[GUID] = mapped_column(
        GUID(),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    is_successful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    check: Mapped["MonitoringCheck"] = relationship("MonitoringCheck", back_populates="samples")
    service: Mapped["Service"] = relationship("Service", back_populates="samples")

    def __repr__(self) -> str:
        return f"<MetricSample(id={self.id}, service_id={self.service_id}, success={self.is_successful}, time={self.response_time_ms}ms)>"

