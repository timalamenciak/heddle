from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from accounts.mixins import RoleRequiredMixin
from accounts.models import Role
from audit.services import record_audit

from .forms import BulkStatusForm, EventForm, ParticipationForm, SegmentForm
from .models import Event, Participation, ParticipationStatus, SavedSegment
from .services import apply_segment_filters, build_invite_zip, get_match_reasons


def _build_filters_from_post(post) -> dict:
    """Build a filter dict directly from POST data (used for live preview)."""
    filters: dict = {}
    for key in ("countries", "continents", "org_types", "expertise_term_ids", "metadata_status"):
        if vals := [v for v in post.getlist(key) if v]:
            filters[key] = vals
    if ft := post.get("free_text", "").strip():
        filters["free_text"] = ft
    for key in ("consent_contact", "consent_public_profile", "has_orcid", "no_critical_issues"):
        if post.get(key):
            filters[key] = True
    for key in ("prior_participation_event_id", "not_invited_to_event_id"):
        if val := post.get(key, "").strip():
            filters[key] = val
    return filters


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class EventListView(RoleRequiredMixin, View):
    required_role = Role.VIEWER
    template_name = "events/event_list.html"

    def get(self, request):
        events = Event.objects.prefetch_related("participations").all()
        return render(request, self.template_name, {"events": events})


class EventCreateView(RoleRequiredMixin, View):
    required_role = Role.ORGANIZER
    template_name = "events/event_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": EventForm(), "title": "New event"})

    def post(self, request):
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            record_audit(request, "event.create", event, changes={"fields": form.changed_data})
            messages.success(request, f'Event "{event.name}" created.')
            return redirect("events:event_detail", pk=event.pk)
        return render(request, self.template_name, {"form": form, "title": "New event"})


class EventEditView(RoleRequiredMixin, View):
    required_role = Role.ORGANIZER
    template_name = "events/event_form.html"

    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        return render(
            request, self.template_name, {"form": EventForm(instance=event), "title": "Edit event"}
        )

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            record_audit(request, "event.update", event, changes={"fields": form.changed_data})
            messages.success(request, "Event updated.")
            return redirect("events:event_detail", pk=event.pk)
        return render(request, self.template_name, {"form": form, "title": "Edit event"})


class EventDetailView(RoleRequiredMixin, View):
    required_role = Role.VIEWER
    template_name = "events/event_detail.html"

    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        participations = event.participations.select_related("person").prefetch_related(
            "person__affiliations__organization"
        )
        bulk_form = BulkStatusForm()
        bulk_form.fields["participation_ids"].choices = [
            (str(p.pk), str(p.person)) for p in participations
        ]
        add_form = ParticipationForm()
        return render(
            request,
            self.template_name,
            {
                "event": event,
                "participations": participations,
                "bulk_form": bulk_form,
                "add_form": add_form,
                "can_edit": request.user.has_min_role(Role.ORGANIZER),
            },
        )


class ParticipationAddView(RoleRequiredMixin, View):
    required_role = Role.ORGANIZER

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        form = ParticipationForm(request.POST)
        if form.is_valid():
            person = form.cleaned_data["person"]
            if Participation.objects.filter(person=person, event=event).exists():
                messages.warning(request, f"{person} is already in this event's roster.")
            else:
                participation = Participation.objects.create(
                    person=person,
                    event=event,
                    role=form.cleaned_data["role"],
                    status=form.cleaned_data["status"],
                    notes=form.cleaned_data.get("notes", ""),
                    created_by=request.user,
                )
                record_audit(request, "participation.create", participation)
                messages.success(request, f"Added {person} to roster.")
        else:
            messages.error(request, "Invalid submission.")
        return redirect("events:event_detail", pk=event.pk)


class ParticipationBulkStatusView(RoleRequiredMixin, View):
    required_role = Role.ORGANIZER

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        ids = request.POST.getlist("participation_ids")
        new_status = request.POST.get("new_status")
        if new_status not in ParticipationStatus.values:
            messages.error(request, "Invalid status.")
            return redirect("events:event_detail", pk=event.pk)
        updated = Participation.objects.filter(pk__in=ids, event=event).update(status=new_status)
        record_audit(
            request,
            "participation.bulk_status",
            event,
            changes={"new_status": new_status, "updated_count": updated},
        )
        messages.success(request, f"Updated {updated} participant(s) to {new_status}.")
        return redirect("events:event_detail", pk=event.pk)


# ---------------------------------------------------------------------------
# Segments
# ---------------------------------------------------------------------------


class SegmentListView(RoleRequiredMixin, View):
    required_role = Role.CONTRIBUTOR
    template_name = "events/segment_list.html"

    def get(self, request):
        segments = SavedSegment.objects.select_related("created_by").all()
        return render(request, self.template_name, {"segments": segments})


class SegmentCreateView(RoleRequiredMixin, View):
    required_role = Role.ORGANIZER
    template_name = "events/segment_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": SegmentForm(), "title": "New segment"})

    def post(self, request):
        form = SegmentForm(request.POST)
        if form.is_valid():
            segment = form.save(commit=False)
            segment.created_by = request.user
            segment.save()
            record_audit(request, "segment.create", segment)
            messages.success(request, f'Segment "{segment.name}" saved.')
            return redirect("events:segment_preview", pk=segment.pk)
        return render(request, self.template_name, {"form": form, "title": "New segment"})


class SegmentEditView(RoleRequiredMixin, View):
    required_role = Role.ORGANIZER
    template_name = "events/segment_form.html"

    def get(self, request, pk):
        segment = get_object_or_404(SavedSegment, pk=pk)
        return render(
            request,
            self.template_name,
            {"form": SegmentForm(instance=segment), "segment": segment, "title": "Edit segment"},
        )

    def post(self, request, pk):
        segment = get_object_or_404(SavedSegment, pk=pk)
        form = SegmentForm(request.POST, instance=segment)
        if form.is_valid():
            form.save()
            record_audit(request, "segment.update", segment)
            messages.success(request, "Segment updated.")
            return redirect("events:segment_preview", pk=segment.pk)
        return render(
            request,
            self.template_name,
            {"form": form, "segment": segment, "title": "Edit segment"},
        )


class SegmentPreviewView(RoleRequiredMixin, View):
    """Full preview page for a saved segment, showing matched people with reasons."""

    required_role = Role.CONTRIBUTOR
    template_name = "events/segment_preview.html"

    def get(self, request, pk):
        segment = get_object_or_404(SavedSegment, pk=pk)
        candidates = apply_segment_filters(segment.filters).prefetch_related(
            "affiliations__organization", "expertise__term"
        )[:200]
        matches = [
            {"person": p, "reasons": get_match_reasons(p, segment.filters)} for p in candidates
        ]
        return render(
            request,
            self.template_name,
            {
                "segment": segment,
                "matches": matches,
                "total": len(matches),
                "can_export": request.user.has_min_role(Role.ORGANIZER),
            },
        )


class SegmentPreviewPartialView(RoleRequiredMixin, View):
    """HTMX partial — POST filter data, returns live preview table fragment."""

    required_role = Role.CONTRIBUTOR
    template_name = "events/segment_preview_partial.html"

    def post(self, request):
        filters = _build_filters_from_post(request.POST)
        candidates = apply_segment_filters(filters).prefetch_related(
            "affiliations__organization", "expertise__term"
        )[:100]
        matches = [{"person": p, "reasons": get_match_reasons(p, filters)} for p in candidates]
        return render(
            request,
            self.template_name,
            {"matches": matches, "total": len(matches)},
        )


class InviteListExportView(RoleRequiredMixin, View):
    required_role = Role.ORGANIZER

    def get(self, request, pk):
        segment = get_object_or_404(SavedSegment, pk=pk)
        zip_bytes = build_invite_zip(segment)
        record_audit(request, "export.invite_list", segment)
        slug = segment.name.replace(" ", "_")[:40]
        response = HttpResponse(zip_bytes, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="invite_{slug}.zip"'
        return response
