from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        CHEF = "chef", "Chef"
        ADMIN = "admin", "Admin"

    class ChefApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        REMOVED = "removed", "Removed"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    chef_approval_status = models.CharField(
        max_length=10,
        choices=ChefApprovalStatus.choices,
        blank=True,
        null=True,
        help_text="Only approved chefs can sign in to chef tools.",
    )
    chef_requested_at = models.DateTimeField(blank=True, null=True)
    chef_approved_at = models.DateTimeField(blank=True, null=True)
    chef_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_chef_profiles",
        blank=True,
        null=True,
    )
    chef_removed_at = models.DateTimeField(blank=True, null=True)
    chef_removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="removed_chef_profiles",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        status = self.get_chef_approval_status_display() if self.is_chef else ""
        role_label = self.get_role_display()
        details = f"{role_label} · {status}" if status else role_label
        return f"{self.user.username} ({details})"

    @property
    def is_chef(self):
        return self.role == self.Role.CHEF

    @property
    def is_approved_chef(self):
        return (
            self.is_chef
            and self.chef_approval_status == self.ChefApprovalStatus.APPROVED
        )

    @property
    def is_removed_chef(self):
        return (
            self.is_chef
            and self.chef_approval_status == self.ChefApprovalStatus.REMOVED
        )

    def approve_as_chef(self, reviewer):
        if not self.is_chef:
            raise ValidationError("Only chef profiles can be approved.")

        approved_at = timezone.now()
        self.chef_approval_status = self.ChefApprovalStatus.APPROVED
        self.chef_approved_at = approved_at
        self.chef_approved_by = reviewer
        self.save(
            update_fields=[
                "chef_approval_status",
                "chef_approved_at",
                "chef_approved_by",
            ]
        )

        if not self.user.is_active:
            self.user.is_active = True
            self.user.save(update_fields=["is_active"])

    def remove_as_chef(self, reviewer):
        if not self.is_chef:
            raise ValidationError("Only chef profiles can be removed.")

        self.chef_approval_status = self.ChefApprovalStatus.REMOVED
        self.chef_removed_at = timezone.now()
        self.chef_removed_by = reviewer
        self.save(
            update_fields=[
                "chef_approval_status",
                "chef_removed_at",
                "chef_removed_by",
            ]
        )

        if self.user.is_active:
            self.user.is_active = False
            self.user.save(update_fields=["is_active"])

    def request_chef_approval(self):
        if not self.is_chef:
            raise ValidationError("Only chef profiles can request chef approval.")

        self.chef_approval_status = self.ChefApprovalStatus.PENDING
        self.chef_requested_at = timezone.now()
        self.chef_approved_at = None
        self.chef_approved_by = None
        self.chef_removed_at = None
        self.chef_removed_by = None
        self.save(
            update_fields=[
                "chef_approval_status",
                "chef_requested_at",
                "chef_approved_at",
                "chef_approved_by",
                "chef_removed_at",
                "chef_removed_by",
            ]
        )


class UserProfile(Profile):
    class Meta:
        proxy = True
        verbose_name = "user profile"
        verbose_name_plural = "user profiles"
        ordering = ["user__username"]


class ChefProfile(Profile):
    class Meta:
        proxy = True
        verbose_name = "chef profile"
        verbose_name_plural = "chef profiles"
        ordering = ["-chef_requested_at", "user__username"]
