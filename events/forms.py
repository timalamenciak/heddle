from django import forms

from core.models import Continent, ExpertiseTerm, MetadataStatus, OrgType, Person

from .models import Event, ParticipationRole, ParticipationStatus, SavedSegment


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "name",
            "event_type",
            "description",
            "start_date",
            "end_date",
            "location",
            "country",
            "continent",
            "website",
            "is_public",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "End date cannot be before start date.")
        return cleaned


class ParticipationForm(forms.Form):
    person = forms.ModelChoiceField(
        queryset=Person.objects.all(),
        label="Person",
        widget=forms.Select(attrs={"class": "w-full border rounded p-2"}),
    )
    role = forms.ChoiceField(choices=ParticipationRole.choices)
    status = forms.ChoiceField(choices=ParticipationStatus.choices)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))


class BulkStatusForm(forms.Form):
    participation_ids = forms.MultipleChoiceField(
        widget=forms.MultipleHiddenInput,
        required=False,
    )
    new_status = forms.ChoiceField(choices=ParticipationStatus.choices)


class SegmentForm(forms.ModelForm):
    """Creates/edits a SavedSegment. Filter fields are converted to/from the JSON blob."""

    # -- Filter fields (not model fields) --
    countries = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Leave empty to match any country.",
    )
    continents = forms.MultipleChoiceField(
        choices=Continent.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    org_types = forms.MultipleChoiceField(
        choices=OrgType.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Organization types",
    )
    expertise_term_ids = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Expertise terms (any match)",
    )
    free_text = forms.CharField(
        required=False,
        label="Free-text search",
        help_text="Matches name, email, or notes.",
    )
    consent_contact = forms.BooleanField(required=False, label="Must have contact consent")
    consent_public_profile = forms.BooleanField(
        required=False, label="Must have public-profile consent"
    )
    has_orcid = forms.BooleanField(required=False, label="Must have an ORCID iD")
    no_critical_issues = forms.BooleanField(
        required=False, label="Exclude people with critical metadata issues"
    )
    prior_participation_event_id = forms.ModelChoiceField(
        queryset=Event.objects.none(),
        required=False,
        label="Attended or confirmed at event",
        empty_label="— any —",
    )
    not_invited_to_event_id = forms.ModelChoiceField(
        queryset=Event.objects.none(),
        required=False,
        label="Not yet invited to event",
        empty_label="— none —",
    )
    metadata_status = forms.MultipleChoiceField(
        choices=MetadataStatus.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Metadata status (any match)",
    )

    class Meta:
        model = SavedSegment
        fields = ["name", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Dynamic choices from DB
        country_vals = (
            Person.objects.exclude(country="")
            .values_list("country", flat=True)
            .distinct()
            .order_by("country")
        )
        self.fields["countries"].choices = [(c, c) for c in country_vals]
        self.fields["expertise_term_ids"].choices = [
            (str(et.id), et.term) for et in ExpertiseTerm.objects.order_by("term")
        ]
        self.fields["prior_participation_event_id"].queryset = Event.objects.all()
        self.fields["not_invited_to_event_id"].queryset = Event.objects.all()

        # Pre-populate filter fields when editing an existing segment
        if self.instance.pk:
            self._load_filters_into_initial(self.instance.filters)

    def _load_filters_into_initial(self, f: dict) -> None:
        for key in (
            "countries",
            "continents",
            "org_types",
            "expertise_term_ids",
            "metadata_status",
        ):  # noqa: E501
            if val := f.get(key):
                self.initial[key] = val
        for key in (
            "free_text",
            "consent_contact",
            "consent_public_profile",
            "has_orcid",
            "no_critical_issues",
        ):
            if key in f:
                self.initial[key] = f[key]
        for key in ("prior_participation_event_id", "not_invited_to_event_id"):
            if val := f.get(key):
                self.initial[key] = val

    def build_filters(self) -> dict:
        """Build the JSON filter dict from cleaned_data."""
        d = self.cleaned_data
        result: dict = {}
        for key in (
            "countries",
            "continents",
            "org_types",
            "expertise_term_ids",
            "metadata_status",
        ):  # noqa: E501
            if vals := list(d.get(key) or []):
                result[key] = vals
        if ft := (d.get("free_text") or "").strip():
            result["free_text"] = ft
        for key in ("consent_contact", "consent_public_profile", "has_orcid", "no_critical_issues"):
            if d.get(key):
                result[key] = True
        if event := d.get("prior_participation_event_id"):
            result["prior_participation_event_id"] = str(event.pk)
        if event := d.get("not_invited_to_event_id"):
            result["not_invited_to_event_id"] = str(event.pk)
        return result

    def save(self, commit: bool = True) -> SavedSegment:
        instance = super().save(commit=False)
        instance.filters = self.build_filters()
        if commit:
            instance.save()
        return instance
