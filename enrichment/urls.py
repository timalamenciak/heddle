from django.urls import path

from . import views

app_name = "enrichment"

urlpatterns = [
    path(
        "enrichment/person/<uuid:pk>/openalex/",
        views.EnrichPersonFromOpenAlexView.as_view(),
        name="person_openalex",
    ),
    path(
        "enrichment/organization/<uuid:pk>/openalex/",
        views.EnrichOrgFromOpenAlexView.as_view(),
        name="org_openalex",
    ),
    path(
        "enrichment/organization/<uuid:pk>/wikidata/",
        views.EnrichOrgFromWikidataView.as_view(),
        name="org_wikidata",
    ),
    path(
        "enrichment/publication/<uuid:pk>/crossref/",
        views.EnrichPublicationFromCrossrefView.as_view(),
        name="pub_crossref",
    ),
    path(
        "enrichment/publication/<uuid:pk>/openalex/",
        views.EnrichPublicationFromOpenAlexView.as_view(),
        name="pub_openalex",
    ),
]
