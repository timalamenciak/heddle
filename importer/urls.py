from django.urls import path

from . import views

app_name = "importer"

urlpatterns = [
    path("import/upload/", views.ImportUploadView.as_view(), name="upload"),
    path("import/<uuid:pk>/map/", views.ImportMapView.as_view(), name="map"),
    path("import/<uuid:pk>/preview/", views.ImportPreviewView.as_view(), name="preview"),
    path("import/<uuid:pk>/applied/", views.ImportAppliedView.as_view(), name="applied"),
]
