from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Profile


class AccountFlowTests(TestCase):
    def test_health_endpoint(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_dashboard_lists_all_three_account_types(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Good food,")
        self.assertContains(response, reverse("register", args=["user"]))
        self.assertContains(response, reverse("register", args=["chef"]))
        self.assertContains(response, reverse("register", args=["admin"]))

    def test_registration_page_shows_selected_account_type(self):
        for role, label in (
            (Profile.Role.USER, "User"),
            (Profile.Role.CHEF, "Chef"),
            (Profile.Role.ADMIN, "Admin"),
        ):
            with self.subTest(role=role):
                response = self.client.get(reverse("register", args=[role]))

                self.assertEqual(response.context["role_label"], label)
                self.assertTrue(response.context["role_description"])
                self.assertContains(response, "You’re joining as")
                self.assertContains(response, label)
                self.assertContains(response, f"{reverse('login')}?role={role}")

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
        self.assertEqual(user.profile.role, Profile.Role.USER)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

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

    def test_existing_user_can_log_in(self):
        user = User.objects.create_user(username="home_chef", password="Savorly123!")
        Profile.objects.create(user=user, role=Profile.Role.CHEF)

        response = self.client.post(
            reverse("login"),
            {"username": "home_chef", "password": "Savorly123!"},
        )

        self.assertRedirects(response, reverse("home"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_login_page_offers_all_account_types(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Who are you signing in as?")
        for role in (Profile.Role.USER, Profile.Role.CHEF, Profile.Role.ADMIN):
            self.assertContains(response, f'value="{role}"')
            self.assertContains(response, role.capitalize())

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

    def test_login_welcome_message_includes_account_type(self):
        user = User.objects.create_user(username="admin_user", password="Savorly123!")
        Profile.objects.create(user=user, role=Profile.Role.ADMIN)

        response = self.client.post(
            reverse("login"),
            {
                "username": "admin_user",
                "password": "Savorly123!",
                "role": Profile.Role.ADMIN,
            },
            follow=True,
        )

        self.assertContains(response, "You’re signing in as Admin.")

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
