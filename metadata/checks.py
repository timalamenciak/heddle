"""Individual check functions. Each function receives a Person or Organization
and calls either _open_issue or _close_issue depending on whether the
condition holds."""

import re
from datetime import timedelta

from django.utils import timezone

from core.identifiers import validate_orcid
from core.models import ORCIDProfile, Organization, Person, Publication

from .models import IssueStatus, MetadataCheck, MetadataIssue

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_check(code: str) -> "MetadataCheck | None":
    try:
        return MetadataCheck.objects.get(code=code, is_enabled=True)
    except MetadataCheck.DoesNotExist:
        return None


def _open_issue(
    mc: MetadataCheck,
    *,
    person: "Person | None" = None,
    org: "Organization | None" = None,
    publication: "Publication | None" = None,
    detail: str = "",
    suggested_fix: str = "",
) -> None:
    """Ensure exactly one open issue exists for this check+record. Ignores IGNORED ones."""
    existing = MetadataIssue.objects.filter(
        metadata_check=mc,
        person=person,
        organization=org,
        publication=publication,
        status__in=[IssueStatus.OPEN, IssueStatus.IGNORED],
    ).first()
    if existing is None:
        MetadataIssue.objects.create(
            metadata_check=mc,
            person=person,
            organization=org,
            publication=publication,
            detail=detail,
            suggested_fix=suggested_fix,
        )
    elif existing.status == IssueStatus.OPEN:
        if existing.detail != detail or existing.suggested_fix != suggested_fix:
            existing.detail = detail
            existing.suggested_fix = suggested_fix
            existing.save(update_fields=["detail", "suggested_fix"])
    # IGNORED → leave it


def _close_issue(
    mc: MetadataCheck,
    *,
    person: "Person | None" = None,
    org: "Organization | None" = None,
    publication: "Publication | None" = None,
) -> None:
    """Auto-resolve any open issue for this check+record."""
    MetadataIssue.objects.filter(
        metadata_check=mc,
        person=person,
        organization=org,
        publication=publication,
        status=IssueStatus.OPEN,
    ).update(status=IssueStatus.RESOLVED, resolved_at=timezone.now())


def _stale_days(mc: MetadataCheck) -> int:
    try:
        return mc.freshness_rule.max_age_days
    except MetadataCheck.freshness_rule.RelatedObjectDoesNotExist:  # type: ignore[attr-defined]
        return 365


# ---------------------------------------------------------------------------
# Person checks
# ---------------------------------------------------------------------------


def check_person_missing_orcid(person: Person) -> None:
    mc = _get_check("person_missing_orcid")
    if not mc:
        return
    if not person.orcid:
        _open_issue(
            mc,
            person=person,
            detail="No ORCID iD has been recorded for this person.",
            suggested_fix=(
                "Ask the person for their ORCID iD at orcid.org and enter it in the ORCID field."
            ),
        )
    else:
        _close_issue(mc, person=person)


def check_person_invalid_orcid(person: Person) -> None:
    mc = _get_check("person_invalid_orcid")
    if not mc:
        return
    if person.orcid and not validate_orcid(person.orcid):
        _open_issue(
            mc,
            person=person,
            detail=f"ORCID value '{person.orcid}' does not match the 0000-0000-0000-000X format.",
            suggested_fix=(
                "Correct the ORCID value to use the standard format, e.g. 0000-0001-2345-6789."
            ),
        )
    else:
        _close_issue(mc, person=person)


def check_person_missing_email(person: Person) -> None:
    mc = _get_check("person_missing_email")
    if not mc:
        return
    if not person.email:
        _open_issue(
            mc,
            person=person,
            detail="No email address is on file for this person.",
            suggested_fix="Add an email address if available.",
        )
    else:
        _close_issue(mc, person=person)


def check_person_missing_country(person: Person) -> None:
    mc = _get_check("person_missing_country")
    if not mc:
        return
    if not person.country:
        _open_issue(
            mc,
            person=person,
            detail="Country of affiliation is not recorded.",
            suggested_fix="Enter the ISO 3166-1 alpha-2 country code (e.g. CA, US, GB).",
        )
    else:
        _close_issue(mc, person=person)


def check_person_missing_continent(person: Person) -> None:
    mc = _get_check("person_missing_continent")
    if not mc:
        return
    if person.country and not person.continent:
        _open_issue(
            mc,
            person=person,
            detail=f"Country '{person.country}' is set but no continent has been derived.",
            suggested_fix="Select the continent from the edit form.",
        )
    else:
        _close_issue(mc, person=person)


def check_person_missing_org(person: Person) -> None:
    mc = _get_check("person_missing_org")
    if not mc:
        return
    if not person.affiliations.exists():
        _open_issue(
            mc,
            person=person,
            detail="No organizational affiliation is recorded for this person.",
            suggested_fix="Link this person to an organization using the affiliation field.",
        )
    else:
        _close_issue(mc, person=person)


def check_person_no_expertise(person: Person) -> None:
    mc = _get_check("person_no_expertise")
    if not mc:
        return
    if not person.expertise.exists():
        _open_issue(
            mc,
            person=person,
            detail="No expertise terms have been tagged for this person.",
            suggested_fix="Add relevant expertise terms via the Django admin.",
        )
    else:
        _close_issue(mc, person=person)


def check_person_no_consent(person: Person) -> None:
    mc = _get_check("person_no_consent")
    if not mc:
        return
    if not person.consent_contact:
        _open_issue(
            mc,
            person=person,
            detail="Consent to contact has not been recorded as given.",
            suggested_fix="Record consent status after confirming with the person directly.",
        )
    else:
        _close_issue(mc, person=person)


def check_person_stale_profile(person: Person) -> None:
    mc = _get_check("person_stale_profile")
    if not mc:
        return
    threshold = _stale_days(mc)
    cutoff = timezone.now() - timedelta(days=threshold)
    if person.updated_at < cutoff:
        delta = (timezone.now() - person.updated_at).days
        _open_issue(
            mc,
            person=person,
            detail=(
                f"This record has not been updated in {delta} days (threshold: {threshold} days)."
            ),
            suggested_fix="Review and re-verify the person's details, then save the record.",
        )
    else:
        _close_issue(mc, person=person)


def check_person_dup_email(person: Person) -> None:
    mc = _get_check("person_dup_email")
    if not mc:
        return
    if not person.email:
        _close_issue(mc, person=person)
        return
    others = Person.objects.filter(email__iexact=person.email).exclude(pk=person.pk)
    if others.exists():
        names = ", ".join(str(p) for p in others[:3])
        _open_issue(
            mc,
            person=person,
            detail=f"Email '{person.email}' is shared with: {names}.",
            suggested_fix="Verify whether these are the same person and merge or correct records.",
        )
    else:
        _close_issue(mc, person=person)


def check_person_dup_name(person: Person) -> None:
    mc = _get_check("person_dup_name")
    if not mc:
        return
    # Only flag if neither record has an ORCID to distinguish them
    if person.orcid:
        _close_issue(mc, person=person)
        return
    others = Person.objects.filter(
        name_normalized=person.name_normalized, orcid__isnull=True
    ).exclude(pk=person.pk)
    if others.exists():
        names = ", ".join(str(p) for p in others[:3])
        _open_issue(
            mc,
            person=person,
            detail=f"Normalized name matches: {names}. Neither record has an ORCID.",
            suggested_fix=(
                "Add an ORCID to distinguish records, or merge duplicates"
                " if they are the same person."
            ),
        )
    else:
        _close_issue(mc, person=person)


# ---------------------------------------------------------------------------
# ORCID sync checks
# ---------------------------------------------------------------------------


def check_person_orcid_sync_stale(person: Person) -> None:
    mc = _get_check("person_orcid_sync_stale")
    if not mc:
        return
    if not person.orcid:
        _close_issue(mc, person=person)
        return
    profile = ORCIDProfile.objects.filter(person=person).first()
    if profile is None:
        _open_issue(
            mc,
            person=person,
            detail="This person has an ORCID iD but it has never been synced.",
            suggested_fix=("Click 'Sync ORCID' on the person's page or run manage.py sync_orcid."),
        )
        return
    threshold = _stale_days(mc)
    cutoff = timezone.now() - timedelta(days=threshold)
    if profile.fetched_at < cutoff:
        delta = (timezone.now() - profile.fetched_at).days
        _open_issue(
            mc,
            person=person,
            detail=(
                f"ORCID record was last synced {delta} days ago (threshold: {threshold} days)."
            ),
            suggested_fix="Re-sync via the person's page or run manage.py sync_orcid.",
        )
    else:
        _close_issue(mc, person=person)


def check_person_orcid_name_divergence(person: Person) -> None:
    mc = _get_check("person_orcid_name_divergence")
    if not mc:
        return
    profile = ORCIDProfile.objects.filter(person=person).first()
    if profile is None:
        _close_issue(mc, person=person)
        return
    given_diff = profile.given_name_remote and (
        profile.given_name_remote.strip().lower() != person.given_name.strip().lower()
    )
    family_diff = profile.family_name_remote and (
        profile.family_name_remote.strip().lower() != person.family_name.strip().lower()
    )
    if given_diff or family_diff:
        remote_name = f"{profile.given_name_remote} {profile.family_name_remote}".strip()
        _open_issue(
            mc,
            person=person,
            detail=(
                f"ORCID public record shows name '{remote_name}',"
                f" but stored name is '{person.full_name}'."
            ),
            suggested_fix=(
                "Check the pending suggestions for this person"
                " and accept or reject the name update."
            ),
        )
    else:
        _close_issue(mc, person=person)


# ---------------------------------------------------------------------------
# Organization checks
# ---------------------------------------------------------------------------


def check_org_missing_country(org: Organization) -> None:
    mc = _get_check("org_missing_country")
    if not mc:
        return
    if not org.country:
        _open_issue(
            mc,
            org=org,
            detail="Country is not recorded for this organization.",
            suggested_fix="Enter the ISO 3166-1 alpha-2 country code.",
        )
    else:
        _close_issue(mc, org=org)


def check_org_missing_continent(org: Organization) -> None:
    mc = _get_check("org_missing_continent")
    if not mc:
        return
    if org.country and not org.continent:
        _open_issue(
            mc,
            org=org,
            detail=f"Country '{org.country}' is set but no continent has been derived.",
            suggested_fix="Select the continent from the edit form.",
        )
    else:
        _close_issue(mc, org=org)


def check_org_missing_website(org: Organization) -> None:
    mc = _get_check("org_missing_website")
    if not mc:
        return
    if not org.website:
        _open_issue(
            mc,
            org=org,
            detail="No website is recorded for this organization.",
            suggested_fix="Add the organization's official website URL.",
        )
    else:
        _close_issue(mc, org=org)


def check_org_missing_ror(org: Organization) -> None:
    mc = _get_check("org_missing_ror")
    if not mc:
        return
    if not org.ror_id:
        _open_issue(
            mc,
            org=org,
            detail="No ROR (Research Organization Registry) identifier has been recorded.",
            suggested_fix="Look up the organization at ror.org and record its ROR ID.",
        )
    else:
        _close_issue(mc, org=org)


def check_org_no_people(org: Organization) -> None:
    mc = _get_check("org_no_people")
    if not mc:
        return
    if not org.affiliations.exists():
        _open_issue(
            mc,
            org=org,
            detail="No people are affiliated with this organization.",
            suggested_fix=(
                "Link people to this organization or remove the organization if it is unused."
            ),
        )
    else:
        _close_issue(mc, org=org)


def check_org_dup_name(org: Organization) -> None:
    mc = _get_check("org_dup_name")
    if not mc:
        return
    others = Organization.objects.filter(name_normalized=org.name_normalized).exclude(pk=org.pk)
    if others.exists():
        names = ", ".join(o.name for o in others[:3])
        _open_issue(
            mc,
            org=org,
            detail=f"Normalized name matches: {names}.",
            suggested_fix="Merge duplicate organizations or adjust the name to distinguish them.",
        )
    else:
        _close_issue(mc, org=org)


def check_org_stale(org: Organization) -> None:
    mc = _get_check("org_stale")
    if not mc:
        return
    threshold = _stale_days(mc)
    cutoff = timezone.now() - timedelta(days=threshold)
    if org.updated_at < cutoff:
        delta = (timezone.now() - org.updated_at).days
        _open_issue(
            mc,
            org=org,
            detail=(
                f"This record has not been updated in {delta} days (threshold: {threshold} days)."
            ),
            suggested_fix=(
                "Review the organization's details and save to reset the freshness clock."
            ),
        )
    else:
        _close_issue(mc, org=org)


# ---------------------------------------------------------------------------
# Dispatch tables
# ---------------------------------------------------------------------------

PERSON_CHECKS = [
    check_person_missing_orcid,
    check_person_invalid_orcid,
    check_person_missing_email,
    check_person_missing_country,
    check_person_missing_continent,
    check_person_missing_org,
    check_person_no_expertise,
    check_person_no_consent,
    check_person_stale_profile,
    check_person_dup_email,
    check_person_dup_name,
    check_person_orcid_sync_stale,
    check_person_orcid_name_divergence,
]

ORG_CHECKS = [
    check_org_missing_country,
    check_org_missing_continent,
    check_org_missing_website,
    check_org_missing_ror,
    check_org_no_people,
    check_org_dup_name,
    check_org_stale,
]


# ---------------------------------------------------------------------------
# Publication checks
# ---------------------------------------------------------------------------

_DOI_FORMAT_RE = re.compile(r"^10\.\d{4,}/\S+$")


def check_publication_missing_doi(pub: Publication) -> None:
    mc = _get_check("pub_missing_doi")
    if not mc:
        return
    if not pub.doi:
        _open_issue(
            mc,
            publication=pub,
            detail="No DOI has been recorded for this publication.",
            suggested_fix="Add a DOI in 10.XXXX/... format if one exists.",
        )
    else:
        _close_issue(mc, publication=pub)


def check_publication_invalid_doi(pub: Publication) -> None:
    mc = _get_check("pub_invalid_doi")
    if not mc:
        return
    if pub.doi and not _DOI_FORMAT_RE.match(pub.doi_normalized):
        _open_issue(
            mc,
            publication=pub,
            detail=f"DOI '{pub.doi}' does not match the expected 10.XXXX/... format.",
            suggested_fix=(
                "Correct the DOI value. Valid DOIs start with '10.' followed by a registrant code."
            ),
        )
    else:
        _close_issue(mc, publication=pub)


def check_publication_duplicate_doi(pub: Publication) -> None:
    mc = _get_check("pub_duplicate_doi")
    if not mc:
        return
    if (
        pub.doi_normalized
        and Publication.objects.filter(doi_normalized=pub.doi_normalized)
        .exclude(pk=pub.pk)
        .exists()
    ):
        _open_issue(
            mc,
            publication=pub,
            detail=f"Another publication record shares DOI '{pub.doi}'.",
            suggested_fix="Merge the duplicate records or correct the DOI.",
        )
    else:
        _close_issue(mc, publication=pub)


def check_publication_unlinked_authors(pub: Publication) -> None:
    mc = _get_check("pub_unlinked_authors")
    if not mc:
        return
    if pub.authorships.filter(person__isnull=True).exists():
        _open_issue(
            mc,
            publication=pub,
            detail="One or more authors on this publication are not linked to a Person record.",
            suggested_fix="Review the authorships and link each to the correct Person.",
        )
    else:
        _close_issue(mc, publication=pub)


def check_publication_unreviewed_import(pub: Publication) -> None:
    mc = _get_check("pub_unreviewed_import")
    if not mc:
        return
    threshold = _stale_days(mc)
    cutoff = timezone.now() - timedelta(days=threshold)
    if pub.source == "orcid_sync" and not pub.is_reviewed and pub.created_at < cutoff:
        delta = (timezone.now() - pub.created_at).days
        _open_issue(
            mc,
            publication=pub,
            detail=(
                f"This publication was imported from ORCID {delta} days ago"
                " and has not been reviewed."
            ),
            suggested_fix="Review the publication details and mark it as reviewed.",
        )
    else:
        _close_issue(mc, publication=pub)


PUBLICATION_CHECKS = [
    check_publication_missing_doi,
    check_publication_invalid_doi,
    check_publication_duplicate_doi,
    check_publication_unlinked_authors,
    check_publication_unreviewed_import,
]
