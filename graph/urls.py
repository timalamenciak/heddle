from django.urls import path

from . import views

app_name = "graph"

urlpatterns = [
    path("graph/", views.GraphExportIndexView.as_view(), name="export_index"),
    path("graph/kgx/full/", views.KGXFullExportView.as_view(), name="kgx_full"),
    path("graph/kgx/event/<uuid:pk>/", views.KGXEventExportView.as_view(), name="kgx_event"),
    path(
        "graph/kgx/segment/<uuid:pk>/",
        views.KGXSegmentExportView.as_view(),
        name="kgx_segment",
    ),
    path(
        "graph/kgx/person/<uuid:pk>/neighbourhood/",
        views.KGXPersonNeighbourhoodExportView.as_view(),
        name="kgx_person_neighbourhood",
    ),
    path(
        "graph/badges/event/<uuid:pk>/",
        views.BadgeCSVEventExportView.as_view(),
        name="badge_event",
    ),
]
