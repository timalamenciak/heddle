"""Small, dependency-free response hardening middleware."""

from django.http import HttpRequest, HttpResponse


class SecurityHeadersMiddleware:
    """Apply a restrictive browser policy to every response.

    Heddle serves all executable assets locally, so production does not need
    broad script or style origins.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response.setdefault(
            "Content-Security-Policy",
            "; ".join(
                [
                    "default-src 'self'",
                    "base-uri 'self'",
                    "connect-src 'self'",
                    "font-src 'self'",
                    "form-action 'self'",
                    "frame-ancestors 'none'",
                    "img-src 'self' data:",
                    "object-src 'none'",
                    "script-src 'self'",
                    "style-src 'self'",
                ]
            ),
        )
        response.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=()")
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        return response
