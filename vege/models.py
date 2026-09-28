from django.conf import settings
from django.db import models


class recipe(models.Model):
    name = models.CharField(max_length=100)
    recipe_description = models.TextField()
    recipe_image = models.ImageField(upload_to="recipe_images/", blank=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="posted_recipes",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name


class Like(models.Model):
    recipe = models.ForeignKey(
        recipe,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipe_likes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("recipe", "user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} likes {self.recipe.name}"


class Comment(models.Model):
    recipe = models.ForeignKey(
        recipe,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipe_comments",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        help_text="Set when this comment is a reply to another comment.",
    )
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_recipe_chef(self):
        """True when the author is the chef who posted the recipe."""
        return self.recipe.posted_by_id == self.user_id

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} on {self.recipe.name}: {self.text[:50]}"


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        LIKE = "like", "Like"
        COMMENT = "comment", "Comment"

    chef = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    recipe = models.ForeignKey(
        recipe,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_notifications",
    )
    notification_type = models.CharField(
        max_length=10,
        choices=NotificationType.choices,
    )
    text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Snapshot of the comment text (for comments) or empty (for likes).",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.notification_type} for {self.chef.username} from {self.sender.username}"
