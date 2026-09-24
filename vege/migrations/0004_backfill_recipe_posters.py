from django.db import migrations


def backfill_legacy_recipe_posters(apps, schema_editor):
    """Backfill legacy recipes only when their chef is unambiguous."""
    recipe_model = apps.get_model("vege", "recipe")
    profile_model = apps.get_model("home", "Profile")

    chef_ids = list(
        profile_model.objects.filter(role="chef")
        .order_by("user_id")
        .values_list("user_id", flat=True)[:2]
    )
    if len(chef_ids) == 1:
        recipe_model.objects.filter(posted_by__isnull=True).update(
            posted_by_id=chef_ids[0]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("vege", "0003_recipe_posted_by"),
        ("home", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            backfill_legacy_recipe_posters,
            migrations.RunPython.noop,
        ),
    ]
