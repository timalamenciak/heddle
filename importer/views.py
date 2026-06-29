import csv
import io

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from accounts.mixins import RoleRequiredMixin
from accounts.models import Role
from audit.services import record_audit

from .forms import ColumnMappingForm, UploadCSVForm
from .models import ImportSession
from .services import CSVImportError, apply_import, inspect_csv_upload, parse_csv, run_preview


def _session_for_user(user, pk, *, lock: bool = False) -> ImportSession:
    """Return an import session owned by the caller; admins may inspect all."""
    qs = ImportSession.objects.all()
    if lock:
        qs = qs.select_for_update()
    if not user.has_min_role(Role.ADMIN):
        qs = qs.filter(created_by=user)
    return get_object_or_404(qs, pk=pk)


class ImportUploadView(RoleRequiredMixin, View):
    required_role = Role.CONTRIBUTOR
    template_name = "importer/upload.html"

    def get(self, request):
        form = UploadCSVForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = UploadCSVForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        uploaded = request.FILES["file"]
        try:
            raw_csv, row_count, file_sha256 = inspect_csv_upload(uploaded)
        except CSVImportError as exc:
            form.add_error("file", str(exc))
            return render(request, self.template_name, {"form": form})

        original_filename = uploaded.name.replace("\\", "/").rsplit("/", 1)[-1][:255]
        session = ImportSession.objects.create(
            raw_csv=raw_csv,
            file_sha256=file_sha256,
            original_filename=original_filename,
            created_by=request.user,
            source_label=form.cleaned_data.get("source_label", ""),
            row_count=row_count,
        )
        record_audit(
            request,
            "import.upload",
            session,
            changes={"row_count": row_count, "sha256": file_sha256},
        )
        return redirect("importer:map", pk=session.pk)


class ImportMapView(RoleRequiredMixin, View):
    required_role = Role.CONTRIBUTOR
    template_name = "importer/map.html"

    def _columns(self, session: ImportSession) -> list[str]:
        reader = csv.DictReader(io.StringIO(session.raw_csv))
        return list(reader.fieldnames or [])

    def get(self, request, pk):
        session = _session_for_user(request.user, pk)
        columns = self._columns(session)
        form = ColumnMappingForm(csv_columns=columns)
        return render(request, self.template_name, {"session": session, "form": form})

    def post(self, request, pk):
        session = _session_for_user(request.user, pk)
        columns = self._columns(session)
        form = ColumnMappingForm(request.POST, csv_columns=columns)
        if not form.is_valid():
            return render(request, self.template_name, {"session": session, "form": form})
        session.column_mapping = form.get_mapping()
        session.status = ImportSession.Status.MAPPED
        session.save(update_fields=["column_mapping", "status"])
        return redirect("importer:preview", pk=session.pk)


class ImportPreviewView(RoleRequiredMixin, View):
    required_role = Role.CONTRIBUTOR
    template_name = "importer/preview.html"

    def get(self, request, pk):
        session = _session_for_user(request.user, pk)
        rows = parse_csv(session.raw_csv, session.column_mapping)
        preview = run_preview(rows, session.source_label)
        return render(request, self.template_name, {"session": session, "preview": preview})

    def post(self, request, pk):
        with transaction.atomic():
            session = _session_for_user(request.user, pk, lock=True)
            if session.status == ImportSession.Status.APPLIED:
                messages.warning(request, "This import has already been applied.")
                return redirect("importer:applied", pk=session.pk)
            if session.status not in {
                ImportSession.Status.MAPPED,
                ImportSession.Status.PREVIEWED,
            }:
                messages.error(request, "Map the CSV columns before applying this import.")
                return redirect("importer:map", pk=session.pk)

            rows = parse_csv(session.raw_csv, session.column_mapping)
            counts = apply_import(rows, session.source_label, session)

            session.status = ImportSession.Status.APPLIED
            session.applied_at = timezone.now()
            session.preview_data = counts
            # Raw uploaded PII is no longer needed after a successful apply.
            session.raw_csv = ""
            session.column_mapping = {}
            session.save(
                update_fields=[
                    "status",
                    "applied_at",
                    "preview_data",
                    "raw_csv",
                    "column_mapping",
                ]
            )
            record_audit(request, "import.apply", session, changes={"counts": counts})

        messages.success(
            request,
            f"Import applied: {counts['created']} created, "
            f"{counts['updated']} updated, {counts['unchanged']} unchanged, "
            f"{counts['errors']} errors.",
        )
        return redirect("importer:applied", pk=session.pk)


class ImportAppliedView(RoleRequiredMixin, View):
    required_role = Role.CONTRIBUTOR
    template_name = "importer/applied.html"

    def get(self, request, pk):
        session = _session_for_user(request.user, pk)
        return render(
            request,
            self.template_name,
            {"session": session, "counts": session.preview_data},
        )
