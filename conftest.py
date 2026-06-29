import pytest

from accounts.models import Role, User


@pytest.fixture
def viewer(db):
    return User.objects.create_user(
        email="viewer@example.com", password="testpass123", role=Role.VIEWER
    )


@pytest.fixture
def contributor(db):
    return User.objects.create_user(
        email="contributor@example.com", password="testpass123", role=Role.CONTRIBUTOR
    )


@pytest.fixture
def organizer(db):
    return User.objects.create_user(
        email="organizer@example.com", password="testpass123", role=Role.ORGANIZER
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@example.com", password="testpass123", role=Role.ADMIN
    )


@pytest.fixture
def superadmin(db):
    return User.objects.create_superuser(email="super@example.com", password="testpass123")
