from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from home.models import Profile

from .models import recipe


class ChefRecipeTests(TestCase):
    def setUp(self):
        self.chef = User.objects.create_user(
            username="chef_recipe",
            password="Savorly123!",
        )
        Profile.objects.create(user=self.chef, role=Profile.Role.CHEF)
        self.client.force_login(self.chef)

    def test_chef_can_see_add_recipe_form_and_table_link(self):
        response = self.client.get(reverse("recipes"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recipe.html")
        self.assertContains(response, 'class="site-navbar"', count=1)
        self.assertContains(response, "Add Recipe")
        self.assertContains(response, "Chef's Table")
        self.assertContains(response, reverse("recipes"))
        self.assertContains(response, reverse("chefs_table"))

    def test_recipe_name_and_description_are_required(self):
        response = self.client.post(reverse("recipes"), {})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(recipe.objects.count(), 0)
        self.assertContains(response, "This field is required.")

    def test_recipe_can_be_added_without_image_and_redirects_to_table(self):
        response = self.client.post(
            reverse("recipes"),
            {
                "recipe_name": "Tomato Soup",
                "recipe_description": "A warm and simple soup.",
            },
        )

        self.assertRedirects(response, reverse("chefs_table"))
        added_recipe = recipe.objects.get()
        self.assertEqual(added_recipe.name, "Tomato Soup")
        self.assertEqual(added_recipe.recipe_description, "A warm and simple soup.")
        self.assertFalse(added_recipe.recipe_image)

    def test_table_lists_added_recipes(self):
        recipe.objects.create(
            name="Lemon Cake",
            recipe_description="Bright and soft.",
        )

        response = self.client.get(reverse("chefs_table"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "chefs_table.html")
        self.assertContains(response, 'class="site-navbar"', count=1)
        self.assertContains(response, "Chef's Table")
        self.assertContains(response, reverse("recipes"))
        self.assertContains(response, "Lemon Cake")
        self.assertContains(response, "<strong>Lemon Cake</strong>")
        self.assertContains(
            response,
            reverse("recipe_details", args=[recipe.objects.get().pk]),
        )
        self.assertContains(response, "Bright and soft.")
        self.assertContains(response, "No image")

    def test_table_description_is_limited_to_thirty_words(self):
        description = " ".join(f"word{number}" for number in range(1, 41))
        recipe.objects.create(name="Long Recipe", recipe_description=description)

        response = self.client.get(reverse("chefs_table"))

        expected_preview = " ".join(f"word{number}" for number in range(1, 31))
        self.assertContains(response, expected_preview)
        self.assertNotContains(response, "word31")

    def test_recipe_details_shows_complete_recipe_in_order(self):
        description = " ".join(f"word{number}" for number in range(1, 41))
        recipe_item = recipe.objects.create(
            name="Detailed Recipe",
            recipe_description=description,
        )

        response = self.client.get(
            reverse("recipe_details", args=[recipe_item.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recipe_details.html")
        self.assertContains(response, 'class="site-navbar"', count=1)
        self.assertEqual(response.context["recipe"], recipe_item)
        self.assertContains(response, description)
        self.assertContains(response, "No image")

        content = response.content.decode()
        name_position = content.index("<h1>Detailed Recipe</h1>")
        image_position = content.index("recipe-details-media")
        description_position = content.index("recipe-details-description")
        self.assertLess(name_position, image_position)
        self.assertLess(image_position, description_position)

    def test_non_chef_cannot_manage_recipes(self):
        user = User.objects.create_user(
            username="regular_recipe_user",
            password="Savorly123!",
        )
        Profile.objects.create(user=user, role=Profile.Role.USER)
        self.client.force_login(user)

        response = self.client.get(reverse("recipes"))

        self.assertRedirects(response, reverse("home"))

        existing_recipe = recipe.objects.create(
            name="Chef only",
            recipe_description="This page is chef only.",
        )
        details_response = self.client.get(
            reverse("recipe_details", args=[existing_recipe.pk])
        )
        self.assertRedirects(details_response, reverse("home"))

        response = self.client.post(
            reverse("recipes"),
            {
                "recipe_name": "Should not be added",
                "recipe_description": "This must be rejected.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(recipe.objects.count(), 1)
