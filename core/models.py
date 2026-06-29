import uuid

from django.conf import settings
from django.db import models


class MetadataStatus(models.TextChoices):
    UNREVIEWED = "unreviewed", "Unreviewed"
    NEEDS_REVIEW = "needs_review", "Needs review"
    VERIFIED = "verified", "Verified"
    STALE = "stale", "Stale"
    CONFLICTING = "conflicting", "Conflicting"
    INCOMPLETE = "incomplete", "Incomplete"


class Continent(models.TextChoices):
    AFRICA = "Africa", "Africa"
    ANTARCTICA = "Antarctica", "Antarctica"
    ASIA = "Asia", "Asia"
    EUROPE = "Europe", "Europe"
    NORTH_AMERICA = "North America", "North America"
    OCEANIA = "Oceania", "Oceania"
    SOUTH_AMERICA = "South America", "South America"


class OrgType(models.TextChoices):
    UNIVERSITY = "university", "University"
    RESEARCH_INSTITUTE = "research_institute", "Research institute"
    NGO = "ngo", "NGO"
    GOVERNMENT = "government", "Government"
    INDUSTRY = "industry", "Industry"
    OTHER = "other", "Other"


class Vocabulary(models.TextChoices):
    ENVO = "ENVO", "ENVO"
    PATO = "PATO", "PATO"
    RO = "RO", "RO"
    CAMO = "CAMO", "CAMO"
    ELMO = "ELMO", "ELMO"
    OPENALEX = "OpenAlex", "OpenAlex"
    WIKIDATA = "Wikidata", "Wikidata"
    GBIF = "GBIF", "GBIF"
    LOCAL = "local", "Local"


def _normalize_name_key(given: str, family: str) -> str:
    return " ".join(f"{given} {family}".lower().split())


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    name_normalized = models.CharField(max_length=255, blank=True, db_index=True)
    country = models.CharField(max_length=2, blank=True)
    continent = models.CharField(max_length=20, blank=True, choices=Continent.choices)
    website = models.URLField(blank=True)
    org_type = models.CharField(max_length=30, blank=True, choices=OrgType.choices)
    ror_id = models.CharField(max_length=50, blank=True, verbose_name="ROR ID")
    wikidata_qid = models.CharField(max_length=20, blank=True, verbose_name="Wikidata QID")
    metadata_status = models.CharField(
        max_length=20, choices=MetadataStatus.choices, default=MetadataStatus.UNREVIEWED
    )
    source = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "organization"
        verbose_name_plural = "organizations"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        self.name_normalized = " ".join(self.name.lower().split())
        super().save(*args, **kwargs)


class Person(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    given_name = models.CharField(max_length=150)
    family_name = models.CharField(max_length=150)
    name_normalized = models.CharField(max_length=301, blank=True, db_index=True)
    email = models.EmailField(blank=True, null=True)
    orcid = models.CharField(
        max_length=19,
        blank=True,
        null=True,
        unique=True,
        help_text="ORCID iD in 0000-0000-0000-000X format",
        verbose_name="ORCID",
    )
    country = models.CharField(max_length=2, blank=True, help_text="ISO 3166-1 alpha-2 code")
    continent = models.CharField(max_length=20, blank=True, choices=Continent.choices)
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    notes_private = models.TextField(blank=True, help_text="Admin-only. Never exported.")
    consent_contact = models.BooleanField(default=False)
    consent_public_profile = models.BooleanField(default=False)
    metadata_status = models.CharField(
        max_length=20, choices=MetadataStatus.choices, default=MetadataStatus.UNREVIEWED
    )
    metadata_last_checked_at = models.DateTimeField(null=True, blank=True)
    metadata_last_verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_people",
    )
    source = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["family_name", "given_name"]
        verbose_name = "person"
        verbose_name_plural = "people"

    def __str__(self) -> str:
        return f"{self.given_name} {self.family_name}".strip()

    def save(self, *args, **kwargs) -> None:
        self.name_normalized = _normalize_name_key(self.given_name, self.family_name)
        super().save(*args, **kwargs)

    @property
    def full_name(self) -> str:
        return f"{self.given_name} {self.family_name}".strip()

    @property
    def primary_organization(self) -> "Organization | None":
        aff = self.affiliations.filter(is_primary=True).select_related("organization").first()
        if aff:
            return aff.organization
        aff = self.affiliations.select_related("organization").first()
        return aff.organization if aff else None


class Affiliation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="affiliations")
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="affiliations"
    )
    role = models.CharField(max_length=150, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    source = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "-start_date"]
        verbose_name = "affiliation"
        verbose_name_plural = "affiliations"
        constraints = [
            models.UniqueConstraint(
                fields=["person", "organization"],
                name="unique_person_organization",
            )
        ]

    def __str__(self) -> str:
        return f"{self.person} @ {self.organization}"


class ExpertiseTerm(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    term = models.CharField(max_length=255, unique=True)
    source_vocabulary = models.CharField(
        max_length=20, choices=Vocabulary.choices, default=Vocabulary.LOCAL
    )
    external_id = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["term"]
        verbose_name = "expertise term"
        verbose_name_plural = "expertise terms"

    def __str__(self) -> str:
        return self.term


class PersonExpertise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="expertise")
    term = models.ForeignKey(ExpertiseTerm, on_delete=models.PROTECT, related_name="person_links")
    source = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["term__term"]
        verbose_name = "person expertise"
        verbose_name_plural = "person expertise"
        constraints = [
            models.UniqueConstraint(
                fields=["person", "term"],
                name="unique_person_expertise",
            )
        ]

    def __str__(self) -> str:
        return f"{self.person} — {self.term}"


def _normalize_doi(doi: str) -> str:
    doi = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix) :]
    return doi


def _normalize_title_key(title: str) -> str:
    return " ".join(title.lower().split())


class Publication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    title_normalized = models.CharField(max_length=500, blank=True, db_index=True)
    doi = models.CharField(max_length=255, blank=True)
    doi_normalized = models.CharField(max_length=255, blank=True, db_index=True)
    year = models.IntegerField(null=True, blank=True)
    venue = models.CharField(max_length=500, blank=True, help_text="Journal or conference name")
    publication_type = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=100, blank=True)
    is_reviewed = models.BooleanField(default=False)
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "title"]
        verbose_name = "publication"
        verbose_name_plural = "publications"

    def __str__(self) -> str:
        return self.title or "(untitled)"

    def save(self, *args, **kwargs) -> None:
        self.title_normalized = _normalize_title_key(self.title)
        self.doi_normalized = _normalize_doi(self.doi) if self.doi else ""
        super().save(*args, **kwargs)


class Authorship(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    publication = models.ForeignKey(
        Publication, on_delete=models.CASCADE, related_name="authorships"
    )
    person = models.ForeignKey(
        Person,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="authorships",
    )
    author_name = models.CharField(
        max_length=300, blank=True, help_text="Name as it appeared; may be unlinked to a Person."
    )
    position = models.PositiveIntegerField(null=True, blank=True)
    source = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position"]
        verbose_name = "authorship"
        verbose_name_plural = "authorships"
        constraints = [
            models.UniqueConstraint(
                fields=["publication", "person"],
                condition=models.Q(person__isnull=False),
                name="unique_publication_person_authorship",
            )
        ]

    def __str__(self) -> str:
        who = str(self.person) if self.person else self.author_name or "(unknown)"
        return f"{who} → {self.publication}"


class Collaboration(models.Model):
    """Coauthorship edge. Canonical ordering: lexically-smaller UUID is person_a."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person_a = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="collaborations_as_a"
    )
    person_b = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="collaborations_as_b"
    )
    publication_count = models.PositiveIntegerField(default=1)
    first_year = models.IntegerField(null=True, blank=True)
    last_year = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "collaboration"
        verbose_name_plural = "collaborations"
        constraints = [
            models.UniqueConstraint(
                fields=["person_a", "person_b"], name="unique_collaboration_pair"
            ),
            models.CheckConstraint(
                condition=~models.Q(person_a=models.F("person_b")),
                name="collaboration_people_differ",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.person_a} × {self.person_b} ({self.publication_count})"


class ORCIDProfile(models.Model):
    """Cached public ORCID record for a person. Refreshed by sync_orcid; no tokens stored."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.OneToOneField(Person, on_delete=models.CASCADE, related_name="orcid_profile")
    fetched_at = models.DateTimeField()
    given_name_remote = models.CharField(max_length=150, blank=True)
    family_name_remote = models.CharField(max_length=150, blank=True)
    raw_record = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ORCID profile"
        verbose_name_plural = "ORCID profiles"

    def __str__(self) -> str:
        return f"ORCID profile for {self.person}"


class ORCIDWork(models.Model):
    """Raw work entry from ORCID public record, staged for Phase 5 publication linking."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="orcid_works")
    profile = models.ForeignKey(ORCIDProfile, on_delete=models.CASCADE, related_name="works")
    put_code = models.IntegerField()
    title = models.CharField(max_length=500, blank=True)
    work_type = models.CharField(max_length=100, blank=True)
    publication_year = models.IntegerField(null=True, blank=True)
    doi = models.CharField(max_length=255, blank=True)
    raw_work = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-publication_year", "title"]
        verbose_name = "ORCID work"
        verbose_name_plural = "ORCID works"
        constraints = [
            models.UniqueConstraint(fields=["person", "put_code"], name="unique_person_put_code")
        ]

    def __str__(self) -> str:
        return f"{self.title} (put-code {self.put_code})"
