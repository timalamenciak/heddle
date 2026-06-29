from django import forms
from django.core.exceptions import ValidationError

from .identifiers import normalize_orcid
from .models import MetadataStatus, Organization, Person


class PersonForm(forms.ModelForm):
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.order_by("name"),
        required=False,
        help_text="Primary organization",
    )
    organization_role = forms.CharField(
        max_length=150,
        required=False,
        help_text="Role at primary organization (e.g. Researcher, PI)",
    )

    class Meta:
        model = Person
        fields = [
            "given_name",
            "family_name",
            "email",
            "orcid",
            "country",
            "continent",
            "website",
            "notes",
            "consent_contact",
            "consent_public_profile",
            "metadata_status",
            "source",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "country": forms.TextInput(attrs={"placeholder": "CA", "maxlength": 2}),
        }
        help_texts = {
            "country": "ISO 3166-1 alpha-2 code (e.g. CA, US, GB)",
            "orcid": "Format: 0000-0000-0000-000X",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        # notes_private only visible to Admin+
        if user and user.has_min_role("admin"):
            self.fields["notes_private"] = forms.CharField(
                label="Notes (private)",
                widget=forms.Textarea(attrs={"rows": 3}),
                required=False,
                help_text="Admin-only. Never exported.",
                initial=self.instance.notes_private if self.instance.pk else "",
            )
        # Pre-populate org fields from existing primary affiliation
        if self.instance.pk:
            primary_org = self.instance.primary_organization
            if primary_org:
                self.fields["organization"].initial = primary_org
                aff = self.instance.affiliations.filter(organization=primary_org).first()
                if aff:
                    self.fields["organization_role"].initial = aff.role

    def clean_orcid(self):
        value = self.cleaned_data.get("orcid")
        if not value:
            return None
        normalized = normalize_orcid(value)
        if normalized is None:
            raise ValidationError("Enter an ORCID with a valid MOD 11-2 check digit.")
        return normalized


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            "name",
            "country",
            "continent",
            "website",
            "org_type",
            "ror_id",
            "metadata_status",
            "source",
        ]
        widgets = {
            "country": forms.TextInput(attrs={"placeholder": "CA", "maxlength": 2}),
        }
        help_texts = {
            "country": "ISO 3166-1 alpha-2 code",
            "ror_id": "Research Organization Registry identifier (e.g. 03rmrcq20)",
        }


class PersonFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={"placeholder": "Name, email, ORCID…"}),
    )
    country = forms.CharField(
        required=False,
        max_length=2,
        widget=forms.TextInput(attrs={"placeholder": "CA", "maxlength": 2}),
    )
    continent = forms.ChoiceField(
        required=False,
        choices=[("", "Any continent")]
        + list(
            (c, c)
            for c in [
                "Africa",
                "Antarctica",
                "Asia",
                "Europe",
                "North America",
                "Oceania",
                "South America",
            ]
        ),
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.order_by("name"),
        required=False,
        empty_label="Any organization",
    )
    missing_orcid = forms.BooleanField(required=False, label="Missing ORCID")
    consent_contact = forms.NullBooleanField(
        required=False,
        label="Consent to contact",
        widget=forms.Select(
            choices=[
                ("", "Any"),
                (True, "Yes"),
                (False, "No"),
            ]
        ),
    )
    metadata_status = forms.ChoiceField(
        required=False,
        choices=[("", "Any status")] + list(MetadataStatus.choices),
    )
