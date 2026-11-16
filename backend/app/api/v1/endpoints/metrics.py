"""
Prometheus-Compatible Application & Telemetry Metrics Endpoint
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.service import Service, MetricSample, HealthStatusEnum

router = APIRouter(tags=["Metrics & Observability"])


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Exposes application telemetry and service health metrics in Prometheus standard plaintext format.",
    response_class=Response,
)
def prometheus_metrics(db: Session = Depends(get_db)) -> Response:
    lines = []
    
    # 1. Total Services Gauge grouped by health status
    lines.append("# HELP healcloud_services_total Total number of registered services by health status.")
    lines.append("# TYPE healcloud_services_total gauge")
    for status_val in HealthStatusEnum:
        count = db.query(Service).filter(Service.health_status == status_val.value).count()
        lines.append(f'healcloud_services_total{{status="{status_val.value}"}} {count}')

    # 2. Metric Samples Total Counter
    success_count = db.query(MetricSample).filter(MetricSample.is_successful.is_(True)).count()
    failure_count = db.query(MetricSample).filter(MetricSample.is_successful.is_(False)).count()
    lines.append("\n# HELP healcloud_health_probes_total Total synthetic health probes executed.")
    lines.append("# TYPE healcloud_health_probes_total counter")
    lines.append(f'healcloud_health_probes_total{{result="success"}} {success_count}')
    lines.append(f'healcloud_health_probes_total{{result="failure"}} {failure_count}')

    # 3. Service Response Time & Consecutive Failures Gauges
    lines.append("\n# HELP healcloud_service_response_time_ms Most recent measured latency in milliseconds.")
    lines.append("# TYPE healcloud_service_response_time_ms gauge")
    lines.append("\n# HELP healcloud_service_consecutive_failures Current consecutive failure counter.")
    lines.append("# TYPE healcloud_service_consecutive_failures gauge")

    services = db.query(Service).limit(100).all()
    for s in services:
        safe_name = s.name.replace('"', '\\"')
        lines.append(
            f'healcloud_service_consecutive_failures{{service_id="{s.id}",name="{safe_name}"}} {s.consecutive_failures}'
        )
        
        # Latest sample
        latest_sample = (
            db.query(MetricSample)
            .filter(MetricSample.service_id == s.id)
            .order_by(MetricSample.timestamp.desc())
            .first()
        )
        if latest_sample:
            lines.append(
                f'healcloud_service_response_time_ms{{service_id="{s.id}",name="{safe_name}"}} {latest_sample.response_time_ms}'
            )

    body = "\n".join(lines) + "\n"
    return Response(content=body, media_type="text/plain; version=0.0.4; charset=utf-8")


@router.get(
    "/metrics/aws",
    summary="AWS Cloud Reliability & Telemetry Status",
    description="Returns the connection, CloudWatch ingestion, and Systems Manager (SSM) driver status for AWS integration.",
)
def aws_reliability_status() -> dict:
    from app.services.aws_adapter import aws_adapter
    return aws_adapter.get_provider_status()


@router.post(
    "/metrics/aws/cloudwatch-push",
    summary="Push Telemetry to Amazon CloudWatch",
    description="Pushes real-time service latency metrics into Amazon CloudWatch under the 'HealCloud/Telemetry' namespace.",
)
def push_to_cloudwatch(
    service_name: str = "payment-gateway",
    latency_ms: float = 48.5,
) -> dict:
    from app.services.aws_adapter import aws_adapter
    return aws_adapter.push_cloudwatch_metric(
        service_name=service_name,
        metric_name="TargetResponseTime",
        value=latency_ms,
        unit="Milliseconds",
    )


@router.post(
    "/metrics/aws/sns-alert",
    summary="Dispatch On-Call SRE Alert via Amazon SNS",
    description="Publishes an immediate emergency incident notification to an Amazon SNS topic.",
)
def trigger_sns_alert(
    service_name: str = "order-processing-api",
    severity: str = "CRITICAL",
    summary: str = "HTTP 503 Service Unavailable burst detected",
) -> dict:
    from app.services.aws_adapter import aws_adapter
    return aws_adapter.publish_sns_incident_alert(
        incident_id="INC-AWS-DEMO-001",
        service_name=service_name,
        severity=severity,
        title=summary,
        hypothesis="Upstream connection pool exhaustion detected. Automated remediation queued.",
    )


@router.post(
    "/metrics/aws/s3-archive",
    summary="Archive Compliance Audit Log to Amazon S3",
    description="Generates an immutable JSON compliance archive of recent system audit logs and stores it in Amazon S3.",
)
def archive_audit_to_s3(db: Session = Depends(get_db)) -> dict:
    from app.services.aws_adapter import aws_adapter
    from app.models.audit import AuditLog

    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(25).all()
    records = [
        {
            "id": str(l.id),
            "action": l.action,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "user_email": l.user_email,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]
    return aws_adapter.export_audit_snapshot_to_s3(audit_records=records)

