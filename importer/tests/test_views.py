import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from accounts.models import Role, User
from audit.models import AuditLog
from importer.models import ImportSession
from importer.services import inspect_csv_upload


@pytest.mark.django_db
def test_contributor_cannot_read_another_users_import(client, contributor):
    other = User.objects.create_user(
        email="other@example.com", password="testpass123", role=Role.CONTRIBUTOR
    )
    session = ImportSession.objects.create(raw_csv="name\nAda\n", created_by=other)
    client.force_login(contributor)
    response = client.get(reverse("importer:map", kwargs={"pk": session.pk}))
    assert response.status_code == 404


@pytest.mark.django_db
@override_settings(CSV_IMPORT_MAX_BYTES=16)
def test_upload_rejects_oversized_csv(client, contributor):
    client.force_login(contributor)
    uploaded = SimpleUploadedFile("people.csv", b"name\n" + b"A" * 20, text_content_type())
    response = client.post(reverse("importer:upload"), {"file": uploaded})
    assert response.status_code == 200
    assert b"CSV files must be" in response.content
    assert ImportSession.objects.count() == 0


def text_content_type() -> str:
    return "text/csv"


@override_settings(CSV_IMPORT_MAX_BYTES=1024, CSV_IMPORT_MAX_ROWS=10, CSV_IMPORT_MAX_COLUMNS=5)
def test_utf16_bom_upload_is_supported():
    uploaded = SimpleUploadedFile(
        "people.csv", "name\nAda Lovelace\n".encode("utf-16"), text_content_type()
    )
    raw_csv, row_count, fingerprint = inspect_csv_upload(uploaded)
    assert raw_csv.startswith("name")
    assert row_count == 1
    assert len(fingerprint) == 64


@pytest.mark.django_db
def test_successful_apply_is_audited_and_erases_raw_csv(client, contributor):
    session = ImportSession.objects.create(
        raw_csv="given_name,family_name\nAda,Lovelace\n",
        column_mapping={"given_name": "given_name", "family_name": "family_name"},
        created_by=contributor,
        status=ImportSession.Status.MAPPED,
        row_count=1,
    )
    client.force_login(contributor)
    response = client.post(reverse("importer:preview", kwargs={"pk": session.pk}))
    assert response.status_code == 302
    session.refresh_from_db()
    assert session.status == ImportSession.Status.APPLIED
    assert session.raw_csv == ""
    assert session.column_mapping == {}
    assert AuditLog.objects.filter(action="import.apply", object_id=str(session.pk)).exists()


@pytest.mark.django_db
def test_unmapped_import_cannot_be_applied(client, contributor):
    session = ImportSession.objects.create(
        raw_csv="name\nAda\n", created_by=contributor, status=ImportSession.Status.UPLOADED
    )
    client.force_login(contributor)
    response = client.post(reverse("importer:preview", kwargs={"pk": session.pk}))
    assert response.status_code == 302
    assert response["Location"] == reverse("importer:map", kwargs={"pk": session.pk})
    session.refresh_from_db()
    assert session.status == ImportSession.Status.UPLOADED
