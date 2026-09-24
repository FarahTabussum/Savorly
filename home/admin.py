from smtplib import SMTPException

from django.contrib import admin, messages
from django.db import transaction

from .emails import send_chef_approval_email
from .models import ChefProfile, Profile, UserProfile


admin.site.site_header = "Savorly administration"
admin.site.site_title = "Savorly admin"
admin.site.index_title = "Community management"


class CommunityProfileAdmin(admin.ModelAdmin):
    list_select_related = ("user",)
    search_fields = ("user__username", "user__email", "user__first_name")
    readonly_fields = ("role",)

    @admin.display(ordering="user__email", description="Email")
    def email(self, obj):
        return obj.user.email

    @admin.display(boolean=True, description="Active")
    def account_active(self, obj):
        return obj.user.is_active

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@admin.register(UserProfile)
class UserProfileAdmin(CommunityProfileAdmin):
    list_display = ("user", "email", "account_active")
    list_filter = ("user__is_active",)
    ordering = ("user__username",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=Profile.Role.USER)


@admin.register(ChefProfile)
class ChefProfileAdmin(CommunityProfileAdmin):
    list_display = (
        "user",
        "email",
        "chef_approval_status",
        "account_active",
        "chef_requested_at",
        "chef_approved_by",
    )
    list_filter = ("chef_approval_status", "user__is_active")
    list_select_related = ("user", "chef_approved_by")
    readonly_fields = CommunityProfileAdmin.readonly_fields + (
        "chef_approval_status",
        "chef_requested_at",
        "chef_approved_at",
        "chef_approved_by",
    )
    ordering = ("-chef_requested_at", "user__username")
    actions = (
        "approve_selected_chefs",
        "resend_approval_emails",
        "remove_selected_chefs",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(role=Profile.Role.CHEF)
            .exclude(
                chef_approval_status=Profile.ChefApprovalStatus.REMOVED,
            )
            .select_related("chef_approved_by")
        )

    @admin.action(description="Approve selected chef registrations")
    def approve_selected_chefs(self, request, queryset):
        candidate_ids = list(
            queryset.filter(
                chef_approval_status=Profile.ChefApprovalStatus.PENDING,
            ).values_list("pk", flat=True)
        )
        approved_users = []
        email_failures = []

        for profile_id in candidate_ids:
            with transaction.atomic():
                profile = (
                    ChefProfile.objects.select_for_update()
                    .select_related("user")
                    .get(pk=profile_id)
                )
                if (
                    profile.chef_approval_status
                    != Profile.ChefApprovalStatus.PENDING
                ):
                    continue
                profile.approve_as_chef(request.user)
                approved_users.append(profile.user)

        for user in approved_users:
            try:
                send_chef_approval_email(user)
            except (OSError, SMTPException, ValueError) as error:
                email_failures.append(f"{user.username} ({error})")

        if approved_users:
            self.message_user(
                request,
                (
                    f"Approved {len(approved_users)} chef registration"
                    f"{'s' if len(approved_users) != 1 else ''}."
                ),
                messages.SUCCESS,
            )

        if email_failures:
            failure_message = (
                "Approval email could not be sent to: "
                f"{', '.join(email_failures)}."
            )
            self.message_user(request, failure_message, messages.ERROR)

        if not approved_users and not email_failures:
            self.message_user(
                request,
                "No pending chef registrations were selected.",
                messages.WARNING,
            )

    @admin.action(description="Resend approval email to selected chefs")
    def resend_approval_emails(self, request, queryset):
        approved_users = list(
            queryset.filter(
                chef_approval_status=Profile.ChefApprovalStatus.APPROVED,
            ).select_related("user")
        )
        sent_count = 0
        failures = []

        for profile in approved_users:
            try:
                send_chef_approval_email(profile.user)
                sent_count += 1
            except (OSError, SMTPException, ValueError) as error:
                failures.append(f"{profile.user.username} ({error})")

        if sent_count:
            self.message_user(
                request,
                f"Sent {sent_count} approval email"
                f"{'s' if sent_count != 1 else ''}.",
                messages.SUCCESS,
            )

        if failures:
            failure_message = (
                "Email could not be sent to: " + ", ".join(failures) + "."
            )
            self.message_user(request, failure_message, messages.ERROR)

        if not approved_users:
            self.message_user(
                request,
                "No approved chef profiles were selected.",
                messages.WARNING,
            )

    @admin.action(description="Remove selected chef profiles")
    def remove_selected_chefs(self, request, queryset):
        profile_ids = list(queryset.values_list("pk", flat=True))
        removed_count = 0

        for profile_id in profile_ids:
            with transaction.atomic():
                profile = (
                    ChefProfile.objects.select_for_update()
                    .select_related("user")
                    .get(pk=profile_id)
                )
                if profile.is_removed_chef:
                    continue
                profile.remove_as_chef(request.user)
                removed_count += 1

        if removed_count:
            self.message_user(
                request,
                (
                    f"Removed {removed_count} chef profile"
                    f"{'s' if removed_count != 1 else ''}. The account"
                    f"{'s are' if removed_count != 1 else ' is'} now inactive"
                    " and can reapply for chef access."
                ),
                messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                "No removable chef profiles were selected.",
                messages.WARNING,
            )
