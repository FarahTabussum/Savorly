from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RecipeForm
from .models import recipe


def _is_chef(user):
    """Return whether a logged-in user is an approved chef."""
    profile = getattr(user, "profile", None)
    return profile is not None and profile.is_approved_chef


def _redirect_non_chef(request):
    messages.error(request, "Only chefs can manage the recipe table.")
    return redirect("home")


def _get_recipe_for_chef(request, pk):
    """Get an owned recipe without exposing another chef's recipe."""
    recipe_item = get_object_or_404(recipe, pk=pk, posted_by=request.user)
    return recipe_item


def _recipe_post_data(request):
    """Normalize the historical and current recipe field names."""
    post_data = request.POST.copy()
    if "recipe_name" not in post_data and "name" in post_data:
        post_data["recipe_name"] = post_data["name"]
    if "recipe_description" not in post_data and "description" in post_data:
        post_data["recipe_description"] = post_data["description"]
    return post_data


@login_required(login_url="login")
def recipes(request):
    """Let a chef add a recipe.

    The listing of submitted recipes lives on the separate Chef's Table page.
    """
    if not _is_chef(request.user):
        return _redirect_non_chef(request)

    if request.method == "POST":
        form = RecipeForm(_recipe_post_data(request), request.FILES)
        if form.is_valid():
            form.instance.posted_by = request.user
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
def recipe_details(request, pk):
    """Display one recipe with its complete description."""
    if not _is_chef(request.user):
        return _redirect_non_chef(request)

    recipe_item = get_object_or_404(recipe, pk=pk)
    return render(request, "recipe_details.html", {"recipe": recipe_item})


@login_required(login_url="login")
def update_recipe(request, pk):
    """Let a chef edit only a recipe that they posted."""
    if not _is_chef(request.user):
        return _redirect_non_chef(request)

    recipe_item = _get_recipe_for_chef(request, pk)

    if request.method == "POST":
        form = RecipeForm(
            _recipe_post_data(request),
            request.FILES,
            instance=recipe_item,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Recipe updated successfully.")
            return redirect("chefs_table")
    else:
        form = RecipeForm(instance=recipe_item)

    return render(
        request,
        "update_recipe.html",
        {"form": form, "recipe": recipe_item},
    )


@login_required(login_url="login")
def delete_recipe(request, id):
    if not _is_chef(request.user):
        return _redirect_non_chef(request)

    queryset = _get_recipe_for_chef(request, id)
    queryset.delete()
    messages.success(request, "Recipe removed from the Chef's Table.")
    return redirect("chefs_table")


# Backwards-friendly alias for callers that use the singular route name.
chef_table = chefs_table
