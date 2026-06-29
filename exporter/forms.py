from django import forms

from .services import PERSON_COLUMNS


class ExportPeopleForm(forms.Form):
    columns = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Columns to export",
    )
    include_bom = forms.BooleanField(
        required=False,
        label="Include UTF-8 BOM (for Excel compatibility)",
        initial=True,
    )

    def __init__(self, *args: object, user: object = None, **kwargs: object):
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        choices = list(PERSON_COLUMNS)
        if user is not None and hasattr(user, "has_min_role") and user.has_min_role("admin"):  # type: ignore[union-attr]
            choices.append(("notes_private", "Notes (private) — admin only"))
            choices.append(("email", "Email — handle with care"))
        self.fields["columns"].choices = choices  # type: ignore[attr-defined]
        if not self.data:
            self.fields["columns"].initial = [c for c, _ in PERSON_COLUMNS]
