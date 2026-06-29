import pytest

from accounts.models import Role, User


@pytest.mark.django_db
class TestUserCreation:
    def test_create_user_with_email(self):
        user = User.objects.create_user(email="test@example.com", password="pass")
        assert user.email == "test@example.com"
        assert user.role == Role.VIEWER
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_email_domain_is_normalized(self):
        # Django only lowercases the domain part, not the local part
        user = User.objects.create_user(email="Test@EXAMPLE.COM", password="pass")
        assert user.email == "Test@example.com"

    def test_create_user_requires_email(self):
        with pytest.raises(ValueError):
            User.objects.create_user(email="", password="pass")

    def test_create_superuser(self):
        user = User.objects.create_superuser(email="super@example.com", password="pass")
        assert user.role == Role.SUPERADMIN
        assert user.is_superuser is True
        assert user.is_staff is True

    def test_str_returns_email(self, viewer):
        assert str(viewer) == "viewer@example.com"

    def test_full_name_with_names(self):
        user = User.objects.create_user(
            email="a@example.com", password="pass", first_name="Ada", last_name="Lovelace"
        )
        assert user.full_name == "Ada Lovelace"

    def test_full_name_fallback_to_email(self):
        user = User.objects.create_user(email="a@example.com", password="pass")
        assert user.full_name == "a@example.com"


@pytest.mark.django_db
class TestIsStaffAutoSync:
    def test_admin_role_sets_is_staff(self, admin_user):
        assert admin_user.is_staff is True

    def test_superadmin_role_sets_is_staff(self, superadmin):
        assert superadmin.is_staff is True

    def test_viewer_role_clears_is_staff(self, viewer):
        assert viewer.is_staff is False

    def test_contributor_role_clears_is_staff(self, contributor):
        assert contributor.is_staff is False

    def test_organizer_role_clears_is_staff(self, organizer):
        assert organizer.is_staff is False

    def test_demoting_admin_clears_is_staff(self, admin_user):
        admin_user.role = Role.VIEWER
        admin_user.save()
        admin_user.refresh_from_db()
        assert admin_user.is_staff is False
