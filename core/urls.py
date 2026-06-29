from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("people/", views.PersonListView.as_view(), name="person_list"),
    path("people/new/", views.PersonCreateView.as_view(), name="person_create"),
    path("people/<uuid:pk>/", views.PersonDetailView.as_view(), name="person_detail"),
    path("people/<uuid:pk>/edit/", views.PersonEditView.as_view(), name="person_edit"),
    path("organizations/", views.OrganizationListView.as_view(), name="organization_list"),
    path("organizations/new/", views.OrganizationEditView.as_view(), name="organization_create"),
    path(
        "organizations/<uuid:pk>/",
        views.OrganizationDetailView.as_view(),
        name="organization_detail",
    ),
    path(
        "organizations/<uuid:pk>/edit/",
        views.OrganizationEditView.as_view(),
        name="organization_edit",
    ),
    path(
        "people/<uuid:pk>/sync-orcid/",
        views.ORCIDSyncView.as_view(),
        name="person_sync_orcid",
    ),
    path(
        "people/<uuid:pk>/import-publications/",
        views.ImportORCIDPublicationsView.as_view(),
        name="person_import_publications",
    ),
    path(
        "publications/<uuid:pk>/",
        views.PublicationDetailView.as_view(),
        name="publication_detail",
    ),
]
