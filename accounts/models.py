import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Role(models.TextChoices):
    SUPERADMIN = "superadmin", "Superadmin"
    ADMIN = "admin", "Admin"
    ORGANIZER = "organizer", "Organizer"
    CONTRIBUTOR = "contributor", "Contributor"
    VIEWER = "viewer", "Viewer"


_ROLE_ORDER: list[str] = [
    Role.VIEWER,
    Role.CONTRIBUTOR,
    Role.ORGANIZER,
    Role.ADMIN,
    Role.SUPERADMIN,
]


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # type: ignore[attr-defined]
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("role", Role.SUPERADMIN)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("role") != Role.SUPERADMIN:
            raise ValueError("Superuser must have the superadmin role")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def save(self, *args, **kwargs):
        # Keep is_staff in sync with role so Django admin access is consistent.
        self.is_staff = self.role in (Role.ADMIN, Role.SUPERADMIN)
        super().save(*args, **kwargs)

    def has_min_role(self, role: str) -> bool:
        """Return True if this user's role is at least as permissive as `role`."""
        try:
            return _ROLE_ORDER.index(self.role) >= _ROLE_ORDER.index(role)
        except ValueError:
            return False
