import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestHealthz:
    def test_healthz_returns_200(self, client):
        response = client.get(reverse("healthz"))
        assert response.status_code == 200

    def test_healthz_returns_json_status_ok(self, client):
        response = client.get(reverse("healthz"))
        assert response.json() == {"status": "ok"}

    def test_healthz_no_auth_required(self, client):
        # Explicitly unauthenticated
        response = client.get(reverse("healthz"))
        assert response.status_code == 200

    def test_security_headers_are_present(self, client):
        response = client.get(reverse("healthz"))
        assert "default-src 'self'" in response["Content-Security-Policy"]
        assert response["Permissions-Policy"] == "camera=(), geolocation=(), microphone=()"


@pytest.mark.django_db
class TestDashboard:
    def test_anonymous_redirected_to_login(self, client):
        response = client.get(reverse("accounts:dashboard"))
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_viewer_can_access_dashboard(self, client, viewer):
        client.force_login(viewer)
        response = client.get(reverse("accounts:dashboard"))
        assert response.status_code == 200

    def test_contributor_can_access_dashboard(self, client, contributor):
        client.force_login(contributor)
        response = client.get(reverse("accounts:dashboard"))
        assert response.status_code == 200

    def test_organizer_can_access_dashboard(self, client, organizer):
        client.force_login(organizer)
        response = client.get(reverse("accounts:dashboard"))
        assert response.status_code == 200

    def test_admin_can_access_dashboard(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get(reverse("accounts:dashboard"))
        assert response.status_code == 200

    def test_superadmin_can_access_dashboard(self, client, superadmin):
        client.force_login(superadmin)
        response = client.get(reverse("accounts:dashboard"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestDjangoAdminAccess:
    """Verify that Django admin access mirrors the is_staff flag."""

    def test_viewer_cannot_access_admin(self, client, viewer):
        client.force_login(viewer)
        response = client.get("/admin/")
        # Django admin redirects non-staff to login
        assert response.status_code == 302

    def test_contributor_cannot_access_admin(self, client, contributor):
        client.force_login(contributor)
        response = client.get("/admin/")
        assert response.status_code == 302

    def test_organizer_cannot_access_admin(self, client, organizer):
        client.force_login(organizer)
        response = client.get("/admin/")
        assert response.status_code == 302

    def test_admin_can_access_admin(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get("/admin/")
        assert response.status_code == 200

    def test_superadmin_can_access_admin(self, client, superadmin):
        client.force_login(superadmin)
        response = client.get("/admin/")
        assert response.status_code == 200

    def test_admin_cannot_delete_user(self, client, admin_user, viewer):
        client.force_login(admin_user)
        url = f"/admin/accounts/user/{viewer.pk}/delete/"
        response = client.get(url)
        # Should be 403 (has_delete_permission returns False for non-superadmin)
        assert response.status_code == 403

    def test_superadmin_can_delete_user(self, client, superadmin, viewer):
        client.force_login(superadmin)
        url = f"/admin/accounts/user/{viewer.pk}/delete/"
        response = client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestLogin:
    def test_login_page_renders(self, client):
        response = client.get("/accounts/login/")
        assert response.status_code == 200

    def test_valid_login_redirects_to_dashboard(self, client, viewer):
        response = client.post(
            "/accounts/login/",
            {"username": "viewer@example.com", "password": "testpass123"},
        )
        assert response.status_code == 302
        assert response["Location"] == "/"

    def test_invalid_login_stays_on_login(self, client, viewer):
        response = client.post(
            "/accounts/login/",
            {"username": "viewer@example.com", "password": "wrong"},
        )
        assert response.status_code == 200

    def test_password_reset_form_renders(self, client):
        response = client.get("/accounts/password_reset/")
        assert response.status_code == 200
