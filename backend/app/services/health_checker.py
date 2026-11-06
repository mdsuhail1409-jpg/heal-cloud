"""
HTTP Health Check Probe Execution Engine
"""

import time
import uuid
from typing import Optional, Tuple
from datetime import datetime, timezone
import httpx
from sqlalchemy.orm import Session

from app.core.ssrf import validate_target_url
from app.core.exceptions import EntityNotFoundException
from app.models.service import (
    Service,
    ServiceEndpoint,
    MonitoringCheck,
    MetricSample,
    HealthStatusEnum,
)


def probe_endpoint(
    endpoint: ServiceEndpoint,
    client: Optional[httpx.Client] = None,
) -> Tuple[bool, Optional[int], float, Optional[str]]:
    """
    Executes an isolated HTTP synthetic health probe against a ServiceEndpoint.
    
    Returns:
    (is_successful, status_code, response_time_ms, error_message)
    """
    # 1. Re-validate URL for SSRF protection at execution time
    try:
        validated_url = validate_target_url(endpoint.url)
    except Exception as exc:
        return False, None, 0.0, f"SSRF Blocked: {str(exc)}"

    timeout_seconds = endpoint.timeout_ms / 1000.0
    headers = {"User-Agent": "HealCloud-Reliability-Probe/1.0"}
    if endpoint.headers and isinstance(endpoint.headers, dict):
        headers.update(endpoint.headers)

    start_time = time.perf_counter()
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    is_successful = False

    try:
        # Use provided client or instantiate scoped one
        if client:
            resp = client.request(
                method=endpoint.method,
                url=validated_url,
                headers=headers,
                timeout=timeout_seconds,
            )
        else:
            with httpx.Client(follow_redirects=False) as http_client:
                resp = http_client.request(
                    method=endpoint.method,
                    url=validated_url,
                    headers=headers,
                    timeout=timeout_seconds,
                )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        status_code = resp.status_code

        if status_code == endpoint.expected_status_code:
            is_successful = True
        else:
            is_successful = False
            error_message = (
                f"Expected HTTP status {endpoint.expected_status_code}, "
                f"received HTTP {status_code}."
            )

    except httpx.TimeoutException:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        is_successful = False
        error_message = f"Connection timed out exceeding {endpoint.timeout_ms}ms threshold."
    except httpx.ConnectError:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        is_successful = False
        error_message = "Failed to establish TCP connection to remote target."
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        is_successful = False
        error_message = f"HTTP check execution error: {str(exc)}"

    return is_successful, status_code, elapsed_ms, error_message


def execute_monitoring_check(
    check_id: uuid.UUID,
    db: Session,
    client: Optional[httpx.Client] = None,
) -> MetricSample:
    """
    Executes a health check, updates service status & failure counters, and logs metric sample.
    """
    check = db.query(MonitoringCheck).filter(MonitoringCheck.id == check_id).first()
    if not check:
        raise EntityNotFoundException("MonitoringCheck", check_id)

    service = db.query(Service).filter(Service.id == check.service_id).first()
    if not service:
        raise EntityNotFoundException("Service", check.service_id)

    endpoint = db.query(ServiceEndpoint).filter(ServiceEndpoint.id == check.endpoint_id).first()
    if not endpoint:
        raise EntityNotFoundException("ServiceEndpoint", check.endpoint_id)

    # Execute synthetic probe
    is_success, status_code, response_ms, error_msg = probe_endpoint(endpoint, client=client)

    now = datetime.now(timezone.utc)
    check.last_checked_at = now

    # Update Service health state
    if is_success:
        service.consecutive_failures = 0
        service.health_status = HealthStatusEnum.HEALTHY.value
        service.last_success_at = now
    else:
        service.consecutive_failures += 1
        if service.consecutive_failures >= check.consecutive_failure_threshold:
            service.health_status = HealthStatusEnum.UNHEALTHY.value
        else:
            service.health_status = HealthStatusEnum.DEGRADED.value
        service.last_failure_at = now

    # Record persistent metric sample
    sample = MetricSample(
        check_id=check.id,
        service_id=service.id,
        timestamp=now,
        status_code=status_code,
        response_time_ms=response_ms,
        is_successful=is_success,
        error_message=error_msg,
    )
    db.add(sample)
    db.add(service)
    db.add(check)
    db.flush()

    # Trigger Incident Detection & Diagnosis evaluation
    from app.services.detection_engine import process_monitoring_sample_for_incidents
    process_monitoring_sample_for_incidents(
        db=db,
        service=service,
        endpoint=endpoint,
        check=check,
        sample=sample,
    )

    return sample

