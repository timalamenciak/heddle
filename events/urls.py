from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    # Events
    path("events/", views.EventListView.as_view(), name="event_list"),
    path("events/create/", views.EventCreateView.as_view(), name="event_create"),
    path("events/<uuid:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path("events/<uuid:pk>/edit/", views.EventEditView.as_view(), name="event_edit"),
    path(
        "events/<uuid:pk>/participation/add/",
        views.ParticipationAddView.as_view(),
        name="participation_add",
    ),
    path(
        "events/<uuid:pk>/participation/bulk/",
        views.ParticipationBulkStatusView.as_view(),
        name="participation_bulk",
    ),
    # Segments
    path("segments/", views.SegmentListView.as_view(), name="segment_list"),
    path("segments/create/", views.SegmentCreateView.as_view(), name="segment_create"),
    path(
        "segments/preview/",
        views.SegmentPreviewPartialView.as_view(),
        name="segment_preview_partial",
    ),
    path("segments/<uuid:pk>/", views.SegmentPreviewView.as_view(), name="segment_preview"),
    path("segments/<uuid:pk>/edit/", views.SegmentEditView.as_view(), name="segment_edit"),
    path(
        "segments/<uuid:pk>/export/",
        views.InviteListExportView.as_view(),
        name="segment_export",
    ),
]
