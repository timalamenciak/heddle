import pytest

from accounts.models import Role


@pytest.mark.django_db
class TestHasMinRole:
    def test_viewer_passes_viewer(self, viewer):
        assert viewer.has_min_role(Role.VIEWER) is True

    def test_viewer_fails_contributor(self, viewer):
        assert viewer.has_min_role(Role.CONTRIBUTOR) is False

    def test_viewer_fails_organizer(self, viewer):
        assert viewer.has_min_role(Role.ORGANIZER) is False

    def test_viewer_fails_admin(self, viewer):
        assert viewer.has_min_role(Role.ADMIN) is False

    def test_viewer_fails_superadmin(self, viewer):
        assert viewer.has_min_role(Role.SUPERADMIN) is False

    def test_contributor_passes_viewer_and_contributor(self, contributor):
        assert contributor.has_min_role(Role.VIEWER) is True
        assert contributor.has_min_role(Role.CONTRIBUTOR) is True
        assert contributor.has_min_role(Role.ORGANIZER) is False

    def test_organizer_passes_up_to_organizer(self, organizer):
        assert organizer.has_min_role(Role.ORGANIZER) is True
        assert organizer.has_min_role(Role.ADMIN) is False

    def test_admin_passes_up_to_admin(self, admin_user):
        assert admin_user.has_min_role(Role.ADMIN) is True
        assert admin_user.has_min_role(Role.SUPERADMIN) is False

    def test_superadmin_passes_all_roles(self, superadmin):
        for role in Role.values:
            assert superadmin.has_min_role(role) is True

    def test_unknown_role_string_returns_false(self, viewer):
        assert viewer.has_min_role("nonexistent") is False


@pytest.mark.django_db
class TestRoleFlags:
    def test_viewer_has_no_staff_no_superuser(self, viewer):
        assert viewer.is_staff is False
        assert viewer.is_superuser is False

    def test_contributor_has_no_staff_no_superuser(self, contributor):
        assert contributor.is_staff is False
        assert contributor.is_superuser is False

    def test_organizer_has_no_staff_no_superuser(self, organizer):
        assert organizer.is_staff is False
        assert organizer.is_superuser is False

    def test_admin_has_is_staff_but_not_superuser(self, admin_user):
        assert admin_user.is_staff is True
        assert admin_user.is_superuser is False

    def test_superadmin_has_both_flags(self, superadmin):
        assert superadmin.is_staff is True
        assert superadmin.is_superuser is True
