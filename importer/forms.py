from django import forms

from .normalize import auto_detect_mapping

FIELD_CHOICES = [
    ("", "— ignore —"),
    ("full_name", "Full name (split into given + family)"),
    ("given_name", "Given name"),
    ("family_name", "Family name"),
    ("email", "Email"),
    ("orcid", "ORCID"),
    ("organization", "Organization"),
    ("organization_role", "Role at organization"),
    ("country", "Country (ISO alpha-2 code or common name)"),
    ("continent", "Continent"),
    ("website", "Website"),
    ("notes", "Notes"),
    ("consent_contact", "Consent to contact"),
]


class UploadCSVForm(forms.Form):
    file = forms.FileField(
        label="CSV file",
        help_text="UTF-8 encoded CSV. First row must be column headers.",
    )
    source_label = forms.CharField(
        max_length=100,
        required=False,
        label="Source label",
        help_text="Optional label to track where this data came from (e.g. 'OERC 2026 registration').",  # noqa: E501
    )


class ColumnMappingForm(forms.Form):
    """Dynamically generated form — one ChoiceField per CSV column."""

    def __init__(self, *args: object, csv_columns: list[str] | None = None, **kwargs: object):
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.csv_columns: list[str] = csv_columns or []
        for i, col in enumerate(self.csv_columns):
            self.fields[f"col_{i}"] = forms.ChoiceField(
                label=col,
                choices=FIELD_CHOICES,
                required=False,
                initial=auto_detect_mapping(col),
            )

    def get_mapping(self) -> dict[str, str]:
        """Return {csv_column_name: field_name} for non-ignored columns."""
        mapping: dict[str, str] = {}
        for i, col in enumerate(self.csv_columns):
            value = self.cleaned_data.get(f"col_{i}", "")
            if value:
                mapping[col] = value
        return mapping
