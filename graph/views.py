"""Graph export views — KGX (nodes.tsv + edges.tsv zip) and badge-tool CSV zip."""

from __future__ import annotations

import io
import json
import zipfile

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import TemplateView

from accounts.mixins import RoleRequiredMixin
from accounts.models import Role
from audit.services import record_audit
from core.models import Person
from events.models import Event, SavedSegment

from .exporters.badge_csv import build_badge_export
from .slices import (
    event_kgx_export,
    full_kgx_export,
    person_neighbourhood_kgx_export,
    segment_kgx_export,
)


class GraphExportIndexView(RoleRequiredMixin, TemplateView):
    template_name = "graph/export_index.html"
    required_role = Role.ORGANIZER

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["events"] = Event.objects.order_by("-start_date")[:50]
        ctx["segments"] = SavedSegment.objects.order_by("-updated_at")[:50]
        return ctx


def _kgx_zip_response(export, filename_base: str) -> HttpResponse:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("nodes.tsv", export.nodes_tsv)
        zf.writestr("edges.tsv", export.edges_tsv)
        zf.writestr("manifest.json", json.dumps(export.manifest, indent=2))
    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type="application/zip")
    resp["Content-Disposition"] = f'attachment; filename="{filename_base}.zip"'
    return resp


class KGXFullExportView(RoleRequiredMixin, View):
    required_role = Role.ORGANIZER

    def get(self, request):
        export = full_kgx_export(generated_by=request.user.email)
        record_audit(
            request,
            "export.kgx.full",
            changes={
                "node_count": export.manifest.get("node_count"),
                "edge_count": export.manifest.get("edge_count"),
            },
        )
        return _kgx_zip_response(export, "heddle_kgx_full")


class KGXEventExportView(RoleRequiredMixin, View):
    required_role = Role.ORGANIZER

    def get(self, request, pk):
        get_object_or_404(Event, pk=pk)
        export = event_kgx_export(pk, generated_by=request.user.email)
        record_audit(request, "export.kgx.event", changes={"event_id": str(pk)})
        return _kgx_zip_response(export, f"heddle_kgx_event_{str(pk)[:8]}")


class KGXSegmentExportView(RoleRequiredMixin, View):
    required_role = Role.ORGANIZER

    def get(self, request, pk):
        get_object_or_404(SavedSegment, pk=pk)
        export = segment_kgx_export(pk, generated_by=request.user.email)
        record_audit(request, "export.kgx.segment", changes={"segment_id": str(pk)})
        return _kgx_zip_response(export, f"heddle_kgx_segment_{str(pk)[:8]}")


class KGXPersonNeighbourhoodExportView(RoleRequiredMixin, View):
    required_role = Role.ORGANIZER

    def get(self, request, pk):
        get_object_or_404(Person, pk=pk)
        try:
            hops = int(request.GET.get("hops", 1))
        except (TypeError, ValueError):
            hops = 1
        hops = min(3, max(1, hops))
        export = person_neighbourhood_kgx_export(pk, hops=hops, generated_by=request.user.email)
        record_audit(
            request,
            "export.kgx.person",
            changes={"person_id": str(pk), "hops": hops},
        )
        return _kgx_zip_response(export, f"heddle_kgx_person_{str(pk)[:8]}_hop{hops}")


class BadgeCSVEventExportView(RoleRequiredMixin, View):
    required_role = Role.ORGANIZER

    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        csv_data, manifest = build_badge_export(event, generated_by=request.user.email)
        record_audit(
            request,
            "export.badges",
            event,
            changes={
                "included": manifest.get("included"),
                "excluded_no_consent": manifest.get("excluded_no_consent"),
            },
        )

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("badges.csv", csv_data)
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        buf.seek(0)
        resp = HttpResponse(buf.read(), content_type="application/zip")
        slug = str(pk)[:8]
        resp["Content-Disposition"] = f'attachment; filename="heddle_badges_{slug}.zip"'
        return resp
