from django.db import models


class recipe(models.Model):
    name = models.CharField(max_length=100)
    recipe_description = models.TextField()
    # An image is a nice extra, but a recipe can be shared without one.
    recipe_image = models.ImageField(upload_to="recipe_images/", blank=True)

    def __str__(self):
        return self.name