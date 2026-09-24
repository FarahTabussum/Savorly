from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from home.models import Profile

from .forms import RecipeForm
from .models import recipe


def _is_chef(user):
    """Return whether a logged-in user has the chef role."""
    profile = getattr(user, "profile", None)
    return profile is not None and profile.role == Profile.Role.CHEF


def _redirect_non_chef(request):
    messages.error(request, "Only chefs can manage the recipe table.")
    return redirect("home")


@login_required(login_url="login")
def recipes(request):
    """Let a chef add a recipe.

    The listing of submitted recipes lives on the separate Chef's Table page.
    """
    if not _is_chef(request.user):
        return _redirect_non_chef(request)

    if request.method == "POST":
        post_data = request.POST.copy()
        if "recipe_name" not in post_data and "name" in post_data:
            post_data["recipe_name"] = post_data["name"]
        if "recipe_description" not in post_data and "description" in post_data:
            post_data["recipe_description"] = post_data["description"]
        form = RecipeForm(post_data, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Recipe added to the Chef's Table.")
            return redirect("chefs_table")
    else:
        form = RecipeForm()

    return render(
        request,
        "recipe.html",
        {"form": form, "recipes": recipe.objects.all()},
    )


@login_required(login_url="login")
def chefs_table(request):
    """Display every recipe that has been added by a chef."""
    if not _is_chef(request.user):
        return _redirect_non_chef(request)

    queryset = recipe.objects.all().order_by("-id")
    return render(request, "chefs_table.html", {"recipes": queryset})


@login_required(login_url="login")
def delete_recipe(request, id):
    if not _is_chef(request.user):
        return _redirect_non_chef(request)

    queryset = get_object_or_404(recipe, id=id)
    queryset.delete()
    messages.success(request, "Recipe removed from the Chef's Table.")
    return redirect("chefs_table")


# Backwards-friendly alias for callers that use the singular route name.
chef_table = chefs_table
