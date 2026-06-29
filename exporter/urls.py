from django.urls import path

from . import views

app_name = "exporter"

urlpatterns = [
    path("export/people/", views.ExportPeopleView.as_view(), name="export_people"),
]
