"""Enrichment trigger views — POST-only, Organizer+ required."""

import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from accounts.mixins import RoleRequiredMixin
from accounts.models import Role
from audit.services import record_audit
from core.models import Organization, Person, Publication

from .services import (
    enrich_org_from_openalex,
    enrich_org_from_wikidata,
    enrich_person_from_openalex,
    enrich_publication_from_crossref,
    enrich_publication_from_openalex,
)

logger = logging.getLogger("heddle.enrichment")


class _EnrichBase(RoleRequiredMixin, View):
    required_role = Role.ORGANIZER

    def _flash(self, request, suggestions: list, source_label: str) -> None:
        if suggestions:
            messages.success(
                request,
                f"{len(suggestions)} new suggestion(s) from {source_label}.",
            )
        else:
            messages.info(request, f"No new suggestions from {source_label}.")


class EnrichPersonFromOpenAlexView(_EnrichBase):
    def post(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        try:
            sugs = enrich_person_from_openalex(person)
            self._flash(request, sugs, "OpenAlex")
            record_audit(
                request,
                "enrichment.openalex.person",
                person,
                changes={"suggestions_created": len(sugs)},
            )
        except Exception:  # noqa: BLE001
            logger.exception("OpenAlex enrichment failed for person %s", pk)
            messages.error(request, "OpenAlex enrichment failed. The error was logged.")
        return redirect("core:person_detail", pk=pk)


class EnrichOrgFromOpenAlexView(_EnrichBase):
    def post(self, request, pk):
        org = get_object_or_404(Organization, pk=pk)
        try:
            sugs = enrich_org_from_openalex(org)
            self._flash(request, sugs, "OpenAlex")
            record_audit(
                request,
                "enrichment.openalex.organization",
                org,
                changes={"suggestions_created": len(sugs)},
            )
        except Exception:  # noqa: BLE001
            logger.exception("OpenAlex enrichment failed for organization %s", pk)
            messages.error(request, "OpenAlex enrichment failed. The error was logged.")
        return redirect("core:organization_detail", pk=pk)


class EnrichOrgFromWikidataView(_EnrichBase):
    def post(self, request, pk):
        org = get_object_or_404(Organization, pk=pk)
        try:
            sugs = enrich_org_from_wikidata(org)
            self._flash(request, sugs, "Wikidata")
            record_audit(
                request,
                "enrichment.wikidata.organization",
                org,
                changes={"suggestions_created": len(sugs)},
            )
        except Exception:  # noqa: BLE001
            logger.exception("Wikidata enrichment failed for organization %s", pk)
            messages.error(request, "Wikidata enrichment failed. The error was logged.")
        return redirect("core:organization_detail", pk=pk)


class EnrichPublicationFromCrossrefView(_EnrichBase):
    def post(self, request, pk):
        pub = get_object_or_404(Publication, pk=pk)
        try:
            sugs = enrich_publication_from_crossref(pub)
            self._flash(request, sugs, "Crossref")
            record_audit(
                request,
                "enrichment.crossref.publication",
                pub,
                changes={"suggestions_created": len(sugs)},
            )
        except Exception:  # noqa: BLE001
            logger.exception("Crossref enrichment failed for publication %s", pk)
            messages.error(request, "Crossref enrichment failed. The error was logged.")
        return redirect("core:publication_detail", pk=pk)


class EnrichPublicationFromOpenAlexView(_EnrichBase):
    def post(self, request, pk):
        pub = get_object_or_404(Publication, pk=pk)
        try:
            sugs = enrich_publication_from_openalex(pub)
            self._flash(request, sugs, "OpenAlex")
            record_audit(
                request,
                "enrichment.openalex.publication",
                pub,
                changes={"suggestions_created": len(sugs)},
            )
        except Exception:  # noqa: BLE001
            logger.exception("OpenAlex enrichment failed for publication %s", pk)
            messages.error(request, "OpenAlex enrichment failed. The error was logged.")
        return redirect("core:publication_detail", pk=pk)
