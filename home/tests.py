from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Profile


class AccountFlowTests(TestCase):
    def create_approved_chef(self, username, password="Savorly123!", email=""):
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        Profile.objects.create(
            user=user,
            role=Profile.Role.CHEF,
            chef_approval_status=Profile.ChefApprovalStatus.APPROVED,
        )
        return user

    def test_health_endpoint(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_dashboard_shows_public_roles_and_admin_login(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Good food,")
        self.assertContains(response, reverse("register", args=["user"]))
        self.assertContains(response, reverse("register", args=["chef"]))
        self.assertContains(response, reverse("admin:login"))
        self.assertNotContains(response, reverse("register", args=["admin"]))
        self.assertContains(response, 'class="site-navbar"', count=1)
        self.assertContains(response, "Recipe")
        self.assertContains(response, reverse("recipes"))
        self.assertContains(response, reverse("chefs_table"))

    def test_authenticated_chef_still_sees_dashboard_at_root(self):
        user = self.create_approved_chef("dashboard_chef")
        self.client.force_login(user)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index.html")
        self.assertContains(response, "Good food,")
        self.assertContains(response, "Recipe")
        self.assertContains(response, reverse("recipes"))
        self.assertNotContains(response, "Add Recipe")

    def test_registration_page_shows_selected_account_type(self):
        for role, label in (
            (Profile.Role.USER, "User"),
            (Profile.Role.CHEF, "Chef"),
        ):
            with self.subTest(role=role):
                response = self.client.get(reverse("register", args=[role]))

                self.assertEqual(response.context["role_label"], label)
                self.assertTrue(response.context["role_description"])
                self.assertContains(response, 'class="site-navbar"', count=1)
                self.assertContains(response, "You’re joining as")
                self.assertContains(response, label)
                self.assertContains(response, f"{reverse('login')}?role={role}")

    def test_admin_registration_is_not_available(self):
        response = self.client.get(reverse("register", args=["admin"]))

        self.assertEqual(response.status_code, 404)

    def test_admin_separates_user_and_chef_profiles(self):
        regular_user = User.objects.create_user(
            username="regular_member",
            password="Savorly123!",
        )
        Profile.objects.create(
            user=regular_user,
            role=Profile.Role.USER,
        )
        waiting_chef = User.objects.create_user(
            username="waiting_admin_chef",
            email="chef@example.com",
            password="Savorly123!",
            is_active=False,
        )
        Profile.objects.create(
            user=waiting_chef,
            role=Profile.Role.CHEF,
            chef_approval_status=Profile.ChefApprovalStatus.PENDING,
        )
        admin_user = User.objects.create_superuser(
            username="profile_admin",
            password="Savorly123!",
        )
        self.client.force_login(admin_user)

        user_profiles = self.client.get(
            reverse("admin:home_userprofile_changelist")
        )
        chef_profiles = self.client.get(
            reverse("admin:home_chefprofile_changelist")
        )
        admin_index = self.client.get(reverse("admin:index"))

        self.assertContains(user_profiles, regular_user.username)
        self.assertNotContains(user_profiles, waiting_chef.username)
        self.assertNotContains(user_profiles, "Approve selected chef registrations")
        self.assertContains(chef_profiles, waiting_chef.username)
        self.assertNotContains(chef_profiles, regular_user.username)
        self.assertContains(chef_profiles, "Pending approval")
        self.assertContains(chef_profiles, "Approve selected chef registrations")
        self.assertContains(admin_index, "User profiles")
        self.assertContains(admin_index, "Chef profiles")

    def test_admin_can_remove_a_chef_profile(self):
        chef = self.create_approved_chef(
            "removable_chef",
            email="removable@example.com",
        )
        profile = chef.profile
        admin_user = User.objects.create_superuser(
            username="removal_admin",
            password="Savorly123!",
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("admin:home_chefprofile_changelist"),
            {
                "action": "remove_selected_chefs",
                "_selected_action": [str(profile.pk)],
            },
        )

        self.assertEqual(response.status_code, 302)
        chef.refresh_from_db()
        profile.refresh_from_db()
        self.assertFalse(chef.is_active)
        self.assertEqual(
            profile.chef_approval_status,
            Profile.ChefApprovalStatus.REMOVED,
        )
        self.assertEqual(profile.chef_removed_by, admin_user)
        self.assertIsNotNone(profile.chef_removed_at)

        chef_profiles = self.client.get(
            reverse("admin:home_chefprofile_changelist")
        )
        self.assertNotContains(chef_profiles, chef.username)

    def test_removed_chef_is_prompted_to_reapply_with_same_username(self):
        chef = User.objects.create_user(
            username="reapply_chef",
            email="old@example.com",
            password="OldPassword123!",
            is_active=False,
        )
        Profile.objects.create(
            user=chef,
            role=Profile.Role.CHEF,
            chef_approval_status=Profile.ChefApprovalStatus.REMOVED,
        )

        login_response = self.client.post(
            reverse("login"),
            {
                "username": "reapply_chef",
                "password": "OldPassword123!",
                "role": Profile.Role.CHEF,
            },
        )

        self.assertEqual(login_response.status_code, 400)
        self.assertContains(
            login_response,
            "This chef profile was removed",
            status_code=400,
        )
        self.assertContains(
            login_response,
            "Register as a chef again",
            status_code=400,
        )
        self.assertTrue(login_response.context["show_chef_reregistration"])
        self.assertNotIn("_auth_user_id", self.client.session)

        register_page = self.client.get(
            f"{reverse('register', args=[Profile.Role.CHEF])}"
            "?username=reapply_chef"
        )
        self.assertEqual(
            register_page.context["form_values"]["username"],
            "reapply_chef",
        )

        reapply_response = self.client.post(
            reverse("register", args=[Profile.Role.CHEF]),
            {
                "username": "reapply_chef",
                "email": "new@example.com",
                "password1": "NewPassword123!",
                "password2": "NewPassword123!",
            },
        )

        self.assertRedirects(
            reapply_response,
            f"{reverse('login')}?role=chef",
            fetch_redirect_response=False,
        )
        chef.refresh_from_db()
        profile = chef.profile
        self.assertEqual(User.objects.filter(username="reapply_chef").count(), 1)
        self.assertFalse(chef.is_active)
        self.assertTrue(chef.check_password("NewPassword123!"))
        self.assertEqual(
            profile.chef_approval_status,
            Profile.ChefApprovalStatus.PENDING,
        )
        self.assertIsNotNone(profile.chef_requested_at)
        self.assertIsNone(profile.chef_approved_at)
        self.assertIsNone(profile.chef_removed_at)
        self.assertIsNone(profile.chef_removed_by)

    def test_user_can_register(self):
        response = self.client.post(
            reverse("register", args=["user"]),
            {
                "username": "table_hugger",
                "email": "hello@example.com",
                "password1": "Savorly123!",
                "password2": "Savorly123!",
            },
        )

        self.assertRedirects(response, reverse("home"))
        user = User.objects.get(username="table_hugger")
        self.assertTrue(user.check_password("Savorly123!"))
        self.assertTrue(user.is_active)
        self.assertEqual(user.profile.role, Profile.Role.USER)
        self.assertIsNone(user.profile.chef_approval_status)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_chef_registration_waits_for_admin_approval(self):
        response = self.client.post(
            reverse("register", args=["chef"]),
            {
                "username": "new_chef",
                "email": "chef@example.com",
                "password1": "Savorly123!",
                "password2": "Savorly123!",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('login')}?role=chef",
            fetch_redirect_response=False,
        )
        new_chef = User.objects.get(username="new_chef")
        self.assertFalse(new_chef.is_active)
        self.assertEqual(new_chef.profile.role, Profile.Role.CHEF)
        self.assertEqual(
            new_chef.profile.chef_approval_status,
            Profile.ChefApprovalStatus.PENDING,
        )
        self.assertIsNotNone(new_chef.profile.chef_requested_at)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_chef_registration_requires_email(self):
        response = self.client.post(
            reverse("register", args=["chef"]),
            {
                "username": "chef_without_email",
                "email": "",
                "password1": "Savorly123!",
                "password2": "Savorly123!",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Enter an email address", status_code=400)
        self.assertFalse(User.objects.filter(username="chef_without_email").exists())

    def test_user_can_register_with_password_similar_to_username(self):
        response = self.client.post(
            reverse("register", args=["user"]),
            {
                "username": "leafy_table",
                "email": "",
                "password1": "leafy_table7",
                "password2": "leafy_table7",
            },
        )

        self.assertRedirects(response, reverse("home"))
        user = User.objects.get(username="leafy_table")
        self.assertTrue(user.check_password("leafy_table7"))

    def test_registration_rejects_duplicate_username(self):
        User.objects.create_user(username="already_here", password="Savorly123!")

        response = self.client.post(
            reverse("register", args=["chef"]),
            {
                "username": "ALREADY_HERE",
                "email": "",
                "password1": "Savorly123!",
                "password2": "Savorly123!",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "That username is already taken.", status_code=400)
        self.assertEqual(User.objects.filter(username="ALREADY_HERE").count(), 0)

    def test_existing_chef_is_redirected_to_recipe_page_after_login(self):
        user = self.create_approved_chef("home_chef")

        response = self.client.post(
            reverse("login"),
            {"username": "home_chef", "password": "Savorly123!"},
        )

        self.assertRedirects(response, reverse("recipes"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_explicit_login_destination_is_preserved_for_chef(self):
        self.create_approved_chef("next_chef")
        destination = f"{reverse('chefs_table')}?from=login"

        response = self.client.post(
            reverse("login"),
            {
                "username": "next_chef",
                "password": "Savorly123!",
                "next": destination,
            },
        )

        self.assertRedirects(response, destination)

    def test_login_page_only_offers_public_account_types(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="site-navbar"', count=1)
        self.assertContains(response, "Who are you signing in as?")
        for role in (Profile.Role.USER, Profile.Role.CHEF):
            self.assertContains(response, f'value="{role}"')
            self.assertContains(response, role.capitalize())
        self.assertNotContains(response, f'value="{Profile.Role.ADMIN}"')
        self.assertContains(response, reverse("admin:login"))
        self.assertContains(response, "secure admin login")

    def test_login_page_can_preselect_account_type(self):
        response = self.client.get(f"{reverse('login')}?role=chef")

        self.assertEqual(response.context["selected_role"], Profile.Role.CHEF)
        self.assertEqual(response.context["selected_role_label"], "Chef")
        self.assertContains(response, "You’re signing in as")
        self.assertContains(response, "checked")

    def test_login_rejects_mismatched_account_type(self):
        user = User.objects.create_user(username="table_user", password="Savorly123!")
        Profile.objects.create(user=user, role=Profile.Role.USER)

        response = self.client.post(
            reverse("login"),
            {
                "username": "table_user",
                "password": "Savorly123!",
                "role": Profile.Role.CHEF,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "registered as User", status_code=400)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_staff_account_must_use_the_admin_login(self):
        User.objects.create_superuser(
            username="admin_user",
            email="admin@example.com",
            password="Savorly123!",
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": "admin_user",
                "password": "Savorly123!",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "secure admin login", status_code=400)
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        PUBLIC_SITE_URL="https://savorly.test",
    )
    def test_admin_approval_unlocks_chef_login_and_sends_email(self):
        chef = User.objects.create_user(
            username="waiting_chef",
            email="waiting@example.com",
            password="Savorly123!",
            is_active=False,
        )
        profile = Profile.objects.create(
            user=chef,
            role=Profile.Role.CHEF,
            chef_approval_status=Profile.ChefApprovalStatus.PENDING,
        )
        admin_user = User.objects.create_superuser(
            username="admin_user",
            email="admin@example.com",
            password="Savorly123!",
        )

        pending_login = self.client.post(
            reverse("login"),
            {
                "username": "waiting_chef",
                "password": "Savorly123!",
                "role": Profile.Role.CHEF,
            },
        )
        self.assertEqual(pending_login.status_code, 400)
        self.assertContains(
            pending_login,
            "awaiting admin approval",
            status_code=400,
        )

        self.client.force_login(admin_user)
        approval_response = self.client.post(
            reverse("admin:home_chefprofile_changelist"),
            {
                "action": "approve_selected_chefs",
                "_selected_action": [str(profile.pk)],
            },
        )

        self.assertEqual(approval_response.status_code, 302)
        profile.refresh_from_db()
        chef.refresh_from_db()
        self.assertEqual(
            profile.chef_approval_status,
            Profile.ChefApprovalStatus.APPROVED,
        )
        self.assertEqual(profile.chef_approved_by, admin_user)
        self.assertIsNotNone(profile.chef_approved_at)
        self.assertTrue(chef.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(chef.email, mail.outbox[0].to)
        self.assertIn("approved", mail.outbox[0].subject.lower())
        self.assertIn(
            "https://savorly.test/login/?role=chef",
            mail.outbox[0].body,
        )

        self.client.logout()
        approved_login = self.client.post(
            reverse("login"),
            {
                "username": "waiting_chef",
                "password": "Savorly123!",
                "role": Profile.Role.CHEF,
            },
        )
        self.assertRedirects(approved_login, reverse("recipes"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), chef.pk)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        PUBLIC_SITE_URL="https://savorly.test",
    )
    def test_admin_can_resend_approval_email(self):
        chef = self.create_approved_chef(
            "approved_chef",
            email="approved@example.com",
        )
        admin_user = User.objects.create_superuser(
            username="email_admin",
            password="Savorly123!",
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("admin:home_chefprofile_changelist"),
            {
                "action": "resend_approval_emails",
                "_selected_action": [str(chef.profile.pk)],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(chef.email, mail.outbox[0].to)
        self.assertIn("approved", mail.outbox[0].subject.lower())

    def test_login_rejects_incorrect_password(self):
        User.objects.create_user(username="home_chef", password="Savorly123!")

        response = self.client.post(
            reverse("login"),
            {"username": "home_chef", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "doesn’t look right", status_code=400)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unknown_role_returns_404(self):
        response = self.client.get(reverse("register", args=["owner"]))
        self.assertEqual(response.status_code, 404)

    def test_logout_requires_post(self):
        user = User.objects.create_user(username="home_chef", password="Savorly123!")
        self.client.force_login(user)

        get_response = self.client.get(reverse("logout"))
        post_response = self.client.post(reverse("logout"))

        self.assertEqual(get_response.status_code, 405)
        self.assertRedirects(post_response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)
