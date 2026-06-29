"""Security helpers shared by views."""

from django.http import HttpRequest
from django.utils.http import url_has_allowed_host_and_scheme


def safe_redirect_target(request: HttpRequest, default: str) -> str:
    """Return a same-origin POST/Referer redirect target or a safe default."""
    candidate = request.POST.get("next") or request.META.get("HTTP_REFERER", "")
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return default
