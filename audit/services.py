"""Application-level audit recording for sensitive actions."""

from __future__ import annotations

import ipaddress
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest

from .models import AuditLog


def _client_ip(request: HttpRequest) -> str | None:
    """Use the socket peer address, never an untrusted forwarding header."""
    value = request.META.get("REMOTE_ADDR", "")
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


def record_audit(
    request: HttpRequest,
    action: str,
    obj: Any | None = None,
    *,
    changes: dict[str, Any] | None = None,
) -> AuditLog:
    """Create an audit event without copying sensitive field values."""
    content_type = ContentType.objects.get_for_model(obj) if obj is not None else None
    return AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action[:64],
        content_type=content_type,
        object_id=str(getattr(obj, "pk", ""))[:64] if obj is not None else "",
        object_repr=str(obj)[:200] if obj is not None else "",
        changes=changes or {},
        ip_address=_client_ip(request),
    )
