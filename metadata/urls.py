from django.urls import path

from . import views

app_name = "metadata"

urlpatterns = [
    path("metadata/", views.MetadataDashboardView.as_view(), name="dashboard"),
    path("metadata/run-checks/", views.RunChecksView.as_view(), name="run_checks"),
    path(
        "metadata/issues/<uuid:pk>/resolve/",
        views.IssueResolveView.as_view(),
        name="issue_resolve",
    ),
    path(
        "metadata/issues/<uuid:pk>/ignore/",
        views.IssueIgnoreView.as_view(),
        name="issue_ignore",
    ),
    path(
        "metadata/people/<uuid:pk>/issues/",
        views.PersonIssuesPanelView.as_view(),
        name="person_issues",
    ),
    path(
        "metadata/organizations/<uuid:pk>/issues/",
        views.OrgIssuesPanelView.as_view(),
        name="org_issues",
    ),
    path("metadata/suggestions/", views.SuggestionListView.as_view(), name="suggestions"),
    path(
        "metadata/suggestions/<uuid:pk>/accept/",
        views.SuggestionAcceptView.as_view(),
        name="suggestion_accept",
    ),
    path(
        "metadata/suggestions/<uuid:pk>/reject/",
        views.SuggestionRejectView.as_view(),
        name="suggestion_reject",
    ),
    path(
        "metadata/suggestions/bulk-accept/",
        views.SuggestionBulkAcceptView.as_view(),
        name="suggestion_bulk_accept",
    ),
]
