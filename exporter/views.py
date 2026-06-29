from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

from accounts.mixins import RoleRequiredMixin
from accounts.models import Role
from audit.services import record_audit
from config.version import __version__
from core.models import Person

from .forms import ExportPeopleForm
from .services import ADMIN_ONLY_COLUMNS, export_people_csv


class ExportPeopleView(RoleRequiredMixin, View):
    required_role = Role.CONTRIBUTOR
    template_name = "exporter/export_people.html"

    def get(self, request):
        form = ExportPeopleForm(user=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = ExportPeopleForm(request.POST, user=request.user)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        columns = list(form.cleaned_data["columns"])

        # Enforce: admin-only columns stripped unless user is admin+
        if not request.user.has_min_role(Role.ADMIN):
            columns = [c for c in columns if c not in ADMIN_ONLY_COLUMNS]

        qs = Person.objects.all().order_by("family_name", "given_name")
        include_bom = form.cleaned_data.get("include_bom", False)
        csv_data = export_people_csv(qs, columns, include_bom=include_bom)
        record_audit(
            request,
            "export.people",
            changes={"columns": columns, "row_count": qs.count()},
        )

        response = HttpResponse(csv_data, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="people_export.csv"'
        response["X-Heddle-Version"] = __version__
        return response
