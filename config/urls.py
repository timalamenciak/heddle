from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def healthz(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
    path("healthz/", healthz, name="healthz"),
    path("", include("core.urls")),
    path("", include("importer.urls")),
    path("", include("exporter.urls")),
    path("", include("metadata.urls")),
    path("", include("events.urls")),
    path("", include("graph.urls")),
    path("", include("enrichment.urls")),
]
