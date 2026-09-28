from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RecipeForm
from .models import Comment, Like, Notification, recipe


def _is_chef(user):
    profile = getattr(user, "profile", None)
    return profile is not None and profile.is_approved_chef


def _redirect_non_chef(request):
    messages.error(request, "Only chefs can manage the recipe table.")
    return redirect("home")


def _get_recipe_for_chef(request, pk):
    recipe_item = get_object_or_404(recipe, pk=pk, posted_by=request.user)
    return recipe_item


def _recipe_post_data(request):
    post_data = request.POST.copy()
    if "recipe_name" not in post_data and "name" in post_data:
        post_data["recipe_name"] = post_data["name"]
    if "recipe_description" not in post_data and "description" in post_data:
        post_data["recipe_description"] = post_data["description"]
    return post_data


def _create_notification(recipe_obj, sender, notification_type, text=""):
    if recipe_obj.posted_by and recipe_obj.posted_by != sender:
        Notification.objects.create(
            chef=recipe_obj.posted_by,
            recipe=recipe_obj,
            sender=sender,
            notification_type=notification_type,
            text=text,
        )


@login_required(login_url="login")
def recipes(request):
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
    """Community recipe table. Chefs can manage their own dishes; everyone
    else can browse them read-only."""
    queryset = recipe.objects.all().order_by("-id")
    return render(
        request,
        "chefs_table.html",
        {
            "recipes": queryset,
            "can_manage": _is_chef(request.user),
        },
    )


@login_required(login_url="login")
def recipe_details(request, pk):
    """Display one recipe with likes, comments, and interaction (any logged-in user)."""
    recipe_item = get_object_or_404(recipe, pk=pk)

    likes_count = recipe_item.likes.count()
    user_has_liked = recipe_item.likes.filter(user=request.user).exists()

    if request.method == "POST":
        action = request.POST.get("action")

        if action in ("like", "unlike"):
            if action == "unlike":
                Like.objects.filter(
                    recipe=recipe_item,
                    user=request.user,
                ).delete()
            else:
                like, created = Like.objects.get_or_create(
                    recipe=recipe_item,
                    user=request.user,
                )
                if created:
                    _create_notification(
                        recipe_item,
                        request.user,
                        Notification.NotificationType.LIKE,
                    )
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "likes_count": recipe_item.likes.count(),
                    "user_has_liked": recipe_item.likes.filter(user=request.user).exists(),
                })
            return redirect("recipe_details", pk=pk)

        elif action == "comment":
            text = request.POST.get("comment_text", "").strip()
            parent = None
            parent_id = request.POST.get("parent_id")
            if parent_id:
                parent = get_object_or_404(
                    Comment,
                    pk=parent_id,
                    recipe=recipe_item,
                )
            if text:
                comment = Comment.objects.create(
                    recipe=recipe_item,
                    user=request.user,
                    text=text,
                    parent=parent,
                )
                _create_notification(
                    recipe_item,
                    request.user,
                    Notification.NotificationType.COMMENT,
                    text=text[:255],
                )
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({
                        "comment": {
                            "id": comment.id,
                            "text": comment.text,
                            "username": comment.user.username,
                            "created_at": comment.created_at.strftime("%b %d, %Y %H:%M"),
                            "parent_id": comment.parent_id,
                            "is_recipe_chef": comment.is_recipe_chef,
                            "can_delete": True,
                        }
                    })
                messages.success(request, "Comment added.")
            elif request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"error": "Comment cannot be empty."}, status=400)
            return redirect("recipe_details", pk=pk)

        elif action == "delete_comment":
            comment_id = request.POST.get("comment_id")
            try:
                comment = Comment.objects.get(
                    pk=comment_id,
                    recipe=recipe_item,
                    user=request.user,
                )
                # Include replies in the count so the UI stays accurate.
                removed = 1 + comment.replies.count()
                # Collect the comment plus any cascading replies so their
                # notifications can be removed too.
                deleted_comments = [comment] + list(comment.replies.all())
                comment.delete()
                # Remove notifications generated by the deleted comment(s).
                for deleted in deleted_comments:
                    Notification.objects.filter(
                        chef=recipe_item.posted_by,
                        recipe=recipe_item,
                        sender=deleted.user,
                        notification_type=Notification.NotificationType.COMMENT,
                        text=deleted.text[:255],
                    ).delete()
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {"deleted": True, "id": comment_id, "removed": removed}
                    )
            except Comment.DoesNotExist:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"error": "Comment not found."}, status=404)
            return redirect("recipe_details", pk=pk)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"error": "Unknown action."}, status=400)

    top_level = (
        recipe_item.comments.filter(parent__isnull=True)
        .select_related("user")
        .prefetch_related("replies")
    )
    return render(
        request,
        "recipe_details.html",
        {
            "recipe": recipe_item,
            "comments": top_level,
            "comment_count": recipe_item.comments.count(),
            "likes_count": likes_count,
            "user_has_liked": user_has_liked,
        },
    )


@login_required(login_url="login")
def update_recipe(request, pk):
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


@login_required(login_url="login")
def notifications(request):
    if not _is_chef(request.user):
        return _redirect_non_chef(request)

    notifications_qs = request.user.notifications.select_related(
        "recipe", "sender"
    ).all()
    unread_count = notifications_qs.filter(is_read=False).count()

    return render(
        request,
        "notifications.html",
        {
            "notifications": notifications_qs,
            "unread_count": unread_count,
        },
    )


@login_required(login_url="login")
def mark_notifications_read(request):
    if not _is_chef(request.user):
        return _redirect_non_chef(request)

    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications")


@login_required(login_url="login")
def mark_notification_read(request, pk):
    """Mark one of the logged-in chef's notifications as read (AJAX or POST)."""
    if request.method != "POST":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"error": "POST required."}, status=405)
        return redirect("notifications")

    notification = get_object_or_404(Notification, pk=pk, chef=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    unread = request.user.notifications.filter(is_read=False).count()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {"read": True, "id": notification.pk, "unread_count": unread}
        )
    return redirect("notifications")


@login_required(login_url="login")
def delete_notification(request, pk):
    """Delete one of the logged-in chef's notifications (AJAX or regular POST)."""
    if request.method != "POST":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"error": "POST required."}, status=405)
        return redirect("notifications")

    notification = get_object_or_404(Notification, pk=pk, chef=request.user)
    notification_id = notification.pk
    notification.delete()

    unread = request.user.notifications.filter(is_read=False).count()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {"deleted": True, "id": notification_id, "unread_count": unread}
        )
    return redirect("notifications")


@login_required(login_url="login")
def unread_notification_count(request):
    if not _is_chef(request.user):
        return JsonResponse({"count": 0})

    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({"count": count})


chef_table = chefs_table
