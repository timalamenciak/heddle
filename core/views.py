import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView

from accounts.mixins import RoleRequiredMixin
from accounts.models import Role
from audit.services import record_audit
from metadata.models import MetadataSuggestion, SuggestionStatus

from .forms import OrganizationForm, PersonFilterForm, PersonForm
from .models import Affiliation, Collaboration, Organization, Person, Publication
from .orcid_service import sync_person_orcid
from .publication_service import import_orcid_works_for_person

PAGE_SIZE = 25
_HX_REQUEST_HEADER = "HTTP_HX_REQUEST"
logger = logging.getLogger("heddle.core")


def _apply_person_filters(qs, form):
    if not form.is_valid():
        return qs
    d = form.cleaned_data
    if d.get("q"):
        q = d["q"]
        qs = qs.filter(
            Q(given_name__icontains=q)
            | Q(family_name__icontains=q)
            | Q(email__icontains=q)
            | Q(orcid__icontains=q)
        )
    if d.get("country"):
        qs = qs.filter(country__iexact=d["country"])
    if d.get("continent"):
        qs = qs.filter(continent=d["continent"])
    if d.get("organization"):
        qs = qs.filter(affiliations__organization=d["organization"])
    if d.get("missing_orcid"):
        qs = qs.filter(orcid__isnull=True)
    if d.get("consent_contact") is not None:
        qs = qs.filter(consent_contact=d["consent_contact"])
    if d.get("metadata_status"):
        qs = qs.filter(metadata_status=d["metadata_status"])
    return qs.distinct()


class PersonListView(LoginRequiredMixin, View):
    template_name = "core/person_list.html"
    partial_template = "core/person_list_results.html"

    def get(self, request):
        form = PersonFilterForm(request.GET or None)
        qs = Person.objects.select_related("verified_by").prefetch_related(
            "affiliations__organization"
        )
        qs = _apply_person_filters(qs, form)
        paginator = Paginator(qs, PAGE_SIZE)
        page = paginator.get_page(request.GET.get("page", 1))

        ctx = {"form": form, "page": page, "paginator": paginator, "total": paginator.count}
        if request.META.get(_HX_REQUEST_HEADER):
            return render(request, self.partial_template, ctx)
        return render(request, self.template_name, ctx)


class PersonDetailView(LoginRequiredMixin, DetailView):
    model = Person
    template_name = "core/person_detail.html"
    context_object_name = "person"

    def get_queryset(self):
        return Person.objects.prefetch_related(
            "affiliations__organization", "expertise__term"
        ).select_related("verified_by")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pending_suggestions"] = MetadataSuggestion.objects.filter(
            person=self.object, status=SuggestionStatus.OPEN
        ).order_by("-created_at")
        ctx["publications"] = self.object.authorships.select_related("publication").order_by(
            "-publication__year", "publication__title"
        )
        ctx["collaborators"] = list(
            Collaboration.objects.filter(person_a=self.object)
            .select_related("person_b")
            .order_by("-publication_count")
        ) + list(
            Collaboration.objects.filter(person_b=self.object)
            .select_related("person_a")
            .order_by("-publication_count")
        )
        ctx["has_orcid_works"] = self.object.orcid_works.exists()
        return ctx


class PersonCreateView(RoleRequiredMixin, View):
    required_role = Role.CONTRIBUTOR
    template_name = "core/person_form.html"

    def get(self, request):
        form = PersonForm(user=request.user)
        return render(request, self.template_name, {"form": form, "action": "Create"})

    def post(self, request):
        form = PersonForm(request.POST, user=request.user)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "action": "Create"})
        person = form.save()
        _handle_org(person, form)
        record_audit(
            request,
            "person.create",
            person,
            changes={"fields": sorted(form.changed_data)},
        )
        messages.success(request, f"Person '{person}' created.")
        return redirect("core:person_detail", pk=person.pk)


class PersonEditView(RoleRequiredMixin, View):
    required_role = Role.CONTRIBUTOR
    template_name = "core/person_form.html"

    def get(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        form = PersonForm(instance=person, user=request.user)
        ctx = {"form": form, "person": person, "action": "Edit"}
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        form = PersonForm(request.POST, instance=person, user=request.user)
        if not form.is_valid():
            return render(
                request, self.template_name, {"form": form, "person": person, "action": "Edit"}
            )
        changed_fields = sorted(form.changed_data)
        person = form.save()
        # notes_private only saved if admin+ and field present
        if request.user.has_min_role(Role.ADMIN) and "notes_private" in form.cleaned_data:
            person.notes_private = form.cleaned_data["notes_private"]
            person.save(update_fields=["notes_private"])
        _handle_org(person, form)
        record_audit(
            request,
            "person.update",
            person,
            changes={"fields": changed_fields},
        )
        messages.success(request, f"Person '{person}' updated.")
        return redirect("core:person_detail", pk=person.pk)


def _handle_org(person: Person, form: PersonForm) -> None:
    """Create or update the primary Affiliation from the form org fields."""
    org = form.cleaned_data.get("organization")
    if not org:
        return
    role = form.cleaned_data.get("organization_role", "")
    aff, _ = Affiliation.objects.get_or_create(
        person=person,
        organization=org,
        defaults={"is_primary": True, "role": role, "source": "manual"},
    )
    # Demote any other primary affiliations, promote this one
    Affiliation.objects.filter(person=person, is_primary=True).exclude(pk=aff.pk).update(
        is_primary=False
    )
    if not aff.is_primary or (role and aff.role != role):
        aff.is_primary = True
        aff.role = role
        aff.save()


class ORCIDSyncView(RoleRequiredMixin, View):
    """POST-only: sync ORCID public record for one person. Creates MetadataSuggestions."""

    required_role = Role.ORGANIZER

    def post(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        try:
            suggestions = sync_person_orcid(person)
            if suggestions:
                messages.success(
                    request,
                    f"Synced ORCID for {person}. {len(suggestions)} new suggestion(s) created.",
                )
            else:
                messages.success(request, f"Synced ORCID for {person}. No new suggestions.")
        except Exception:  # noqa: BLE001
            logger.exception("ORCID sync failed for person %s", person.pk)
            messages.error(request, "ORCID sync failed. The error was logged for review.")
        else:
            record_audit(
                request,
                "person.orcid_sync",
                person,
                changes={"suggestions_created": len(suggestions)},
            )
        return redirect("core:person_detail", pk=person.pk)


class ImportORCIDPublicationsView(RoleRequiredMixin, View):
    """POST-only: import ORCIDWork records as Publications for one person."""

    required_role = Role.ORGANIZER

    def post(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        counts = import_orcid_works_for_person(person)
        record_audit(request, "person.publications_import", person, changes={"counts": counts})
        messages.success(
            request,
            f"Imported publications for {person}: "
            f"{counts['created']} new, {counts['merged']} merged, "
            f"{counts['authors_linked']} authorships linked.",
        )
        return redirect("core:person_detail", pk=person.pk)


class PublicationDetailView(LoginRequiredMixin, DetailView):
    model = Publication
    template_name = "core/publication_detail.html"
    context_object_name = "pub"

    def get_queryset(self):
        return Publication.objects.prefetch_related("authorships__person", "suggestions")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from enrichment.models import EnrichmentLog
        from metadata.models import MetadataSuggestion, SuggestionStatus

        ctx["pending_suggestions"] = MetadataSuggestion.objects.filter(
            publication=self.object, status=SuggestionStatus.OPEN
        ).order_by("-created_at")
        ctx["enrichment_log"] = EnrichmentLog.objects.filter(target_id=self.object.pk).order_by(
            "-fetched_at"
        )[:10]
        return ctx


class OrganizationListView(LoginRequiredMixin, View):
    template_name = "core/organization_list.html"

    def get(self, request):
        q = request.GET.get("q", "")
        qs = Organization.objects.all()
        if q:
            qs = qs.filter(name__icontains=q)
        paginator = Paginator(qs, PAGE_SIZE)
        page = paginator.get_page(request.GET.get("page", 1))
        return render(request, self.template_name, {"page": page, "q": q})


class OrganizationDetailView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = "core/organization_detail.html"
    context_object_name = "org"

    def get_queryset(self):
        return Organization.objects.prefetch_related("affiliations__person")


class OrganizationEditView(RoleRequiredMixin, View):
    required_role = Role.CONTRIBUTOR
    template_name = "core/organization_form.html"

    def _get_form_and_org(self, request, pk=None):
        org = get_object_or_404(Organization, pk=pk) if pk else None
        if request.method == "POST":
            form = OrganizationForm(request.POST, instance=org)
        else:
            form = OrganizationForm(instance=org)
        return form, org

    def get(self, request, pk=None):
        form, org = self._get_form_and_org(request, pk)
        action = "Edit" if pk else "Create"
        return render(request, self.template_name, {"form": form, "org": org, "action": action})

    def post(self, request, pk=None):
        form, org = self._get_form_and_org(request, pk)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"form": form, "org": org, "action": "Edit" if pk else "Create"},
            )
        changed_fields = sorted(form.changed_data)
        org = form.save()
        record_audit(
            request,
            "organization.update" if pk else "organization.create",
            org,
            changes={"fields": changed_fields},
        )
        messages.success(request, f"Organization '{org}' saved.")
        return redirect("core:organization_detail", pk=org.pk)
