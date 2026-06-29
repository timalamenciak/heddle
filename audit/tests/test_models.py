import pytest

from audit.models import AuditLog


@pytest.mark.django_db
class TestAuditLog:
    def test_create_audit_log_without_user(self):
        log = AuditLog.objects.create(
            action="create",
            object_repr="SomeObject(1)",
            changes={"field": ["old", "new"]},
        )
        assert log.pk is not None
        assert log.user is None
        assert log.action == "create"

    def test_create_audit_log_with_user(self, viewer):
        log = AuditLog.objects.create(
            user=viewer,
            action="update",
            object_repr="Person(abc)",
            changes={"first_name": ["Alice", "Alicia"]},
            ip_address="127.0.0.1",
        )
        assert log.user == viewer
        assert log.ip_address == "127.0.0.1"

    def test_audit_log_has_uuid_pk(self):
        log = AuditLog.objects.create(action="delete", object_repr="Test")
        assert len(str(log.pk)) == 36  # UUID format

    def test_audit_log_ordering_newest_first(self):
        import datetime

        from django.utils import timezone

        # Use update() to assign deterministic timestamps regardless of clock resolution.
        log1 = AuditLog.objects.create(action="first", object_repr="A")
        AuditLog.objects.filter(pk=log1.pk).update(
            created_at=timezone.now() - datetime.timedelta(seconds=5)
        )
        AuditLog.objects.create(action="second", object_repr="B")
        logs = list(AuditLog.objects.all())
        assert logs[0].action == "second"
        assert logs[1].action == "first"

    def test_str_representation(self):
        log = AuditLog(action="create", object_repr="Person(x)")
        assert "create" in str(log)
        assert "Person(x)" in str(log)
