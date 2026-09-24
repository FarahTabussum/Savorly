from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from .models import Profile


ROLE_DETAILS = {
    "user": {
        "label": "User",
        "description": (
            "Create an account to save favorite recipes, plan meals, and cook "
            "along with the Savorly community."
        ),
    },
    "chef": {
        "label": "Chef",
        "description": (
            "Apply to bring your recipes to the table. Once approved, you can "
            "build a community of home cooks ready to make your dishes."
        ),
    },
}

ROLE_OPTIONS = tuple(
    {"value": role, "label": details["label"]}
    for role, details in ROLE_DETAILS.items()
)


def _role_from_request(request):
    return (request.POST.get("role") or request.GET.get("role") or "").strip()


def _landing_url_for(user):
    """Return the landing page for an authenticated account role."""
    profile = getattr(user, "profile", None)
    if profile is not None and profile.is_approved_chef:
        return reverse("recipes")
    return reverse("home")


def _login_destination(user, next_url):
    """Use a role-specific landing page when no explicit destination is given."""
    if next_url == reverse("home"):
        return _landing_url_for(user)
    return next_url


def home(request):
    return render(request, "index.html")


def _role_details(role):
    details = ROLE_DETAILS.get(role)
    if details is None:
        raise Http404("Unknown account type")
    return details


def register(request, role):
    details = _role_details(role)
    is_chef_application = role == Profile.Role.CHEF

    if request.user.is_authenticated:
        return redirect("home")

    form_values = {
        "username": (
            request.GET.get("username", "").strip() if is_chef_application else ""
        ),
        "email": "",
    }
    errors = {}
    removed_chef_profile = None

    if request.method == "POST":
        form_values = {
            "username": request.POST.get("username", "").strip(),
            "email": request.POST.get("email", "").strip(),
        }
        password = request.POST.get("password1", "")
        password_confirmation = request.POST.get("password2", "")
        username = form_values["username"]
        email = form_values["email"]

        if not username:
            errors["username"] = "Please choose a username."
        elif len(username) > 150:
            errors["username"] = "Username must be 150 characters or fewer."
        elif not all(
            character.isalnum() or character in "@.+-_" for character in username
        ):
            errors["username"] = (
                "Use only letters, numbers, and the characters @ . + - _."
            )
        else:
            existing_user = User.objects.filter(username__iexact=username).first()
            if existing_user is not None:
                existing_profile = getattr(existing_user, "profile", None)
                if (
                    is_chef_application
                    and existing_profile is not None
                    and existing_profile.is_removed_chef
                ):
                    removed_chef_profile = existing_profile
                else:
                    errors["username"] = "That username is already taken."

        if not email and is_chef_application:
            errors["email"] = (
                "Enter an email address so we can confirm your approval."
            )
        elif email:
            try:
                validate_email(email)
            except ValidationError:
                errors["email"] = "Please enter a valid email address."

        if not password:
            errors["password1"] = "Please create a password."
        else:
            try:
                validate_password(password, User(username=username, email=email))
            except ValidationError as error:
                errors["password1"] = " ".join(error.messages)

        if not password_confirmation:
            errors["password2"] = "Please confirm your password."
        elif password and password != password_confirmation:
            errors["password2"] = "The two passwords do not match."

        if not errors:
            try:
                with transaction.atomic():
                    if removed_chef_profile is not None:
                        profile = (
                            Profile.objects.select_for_update()
                            .select_related("user")
                            .get(pk=removed_chef_profile.pk)
                        )
                        if not profile.is_removed_chef:
                            raise IntegrityError(
                                "Chef profile is no longer removable."
                            )

                        user = profile.user
                        user.email = email
                        user.set_password(password)
                        user.is_active = False
                        user.save()
                        profile.request_chef_approval()
                    else:
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            password=password,
                            is_active=not is_chef_application,
                        )
                        Profile.objects.create(
                            user=user,
                            role=role,
                            chef_approval_status=(
                                Profile.ChefApprovalStatus.PENDING
                                if is_chef_application
                                else None
                            ),
                            chef_requested_at=(
                                timezone.now() if is_chef_application else None
                            ),
                        )
            except IntegrityError:
                errors["username"] = "That username is already taken."
            else:
                if is_chef_application:
                    messages.success(
                        request,
                        "Your chef application is awaiting admin approval. "
                        "We’ll email you as soon as you can join the table.",
                    )
                    return redirect(f"{reverse('login')}?role=chef")

                login(request, user)
                messages.success(
                    request,
                    f"Welcome to Savorly, {details['label']}! Your account is ready.",
                )
                return redirect(_landing_url_for(user))

    context = {
        **details,
        "role": role,
        "role_label": details["label"],
        "role_description": details["description"],
        "form_values": form_values,
        "errors": errors,
    }
    return render(request, "register.html", context, status=400 if errors else 200)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    form_values = {"username": ""}
    form_error = ""
    show_chef_reregistration = False
    next_url = _safe_next_url(request)
    selected_role_value = _role_from_request(request)
    selected_role = (
        selected_role_value if selected_role_value in ROLE_DETAILS else ""
    )

    if request.method == "POST":
        form_values["username"] = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        next_url = _safe_next_url(request)
        selected_role_value = _role_from_request(request)
        selected_role = (
            selected_role_value if selected_role_value in ROLE_DETAILS else ""
        )

        if selected_role_value and not selected_role:
            form_error = "Choose User or Chef as your account type."
        elif not form_values["username"] or not password:
            form_error = "Enter both your username and password."
        else:
            user = authenticate(
                request,
                username=form_values["username"],
                password=password,
            )
            if user is None:
                inactive_user = User.objects.filter(
                    username=form_values["username"]
                ).first()
                if inactive_user and inactive_user.check_password(password):
                    inactive_profile = getattr(inactive_user, "profile", None)
                    if (
                        inactive_profile is not None
                        and inactive_profile.is_removed_chef
                    ):
                        form_error = (
                            "This chef profile was removed. Register again to "
                            "request a new chef account."
                        )
                        show_chef_reregistration = True
                    elif (
                        inactive_profile is not None
                        and inactive_profile.is_chef
                        and inactive_profile.chef_approval_status
                        == Profile.ChefApprovalStatus.PENDING
                    ):
                        form_error = (
                            "Your chef application is still awaiting admin approval."
                        )
                    else:
                        form_error = "This account is not active."
                else:
                    form_error = "That username or password doesn’t look right."
            else:
                profile = getattr(user, "profile", None)
                account_role = profile.role if profile is not None else None
                if user.is_staff or account_role == Profile.Role.ADMIN:
                    form_error = (
                        "Administrator accounts must use the secure admin login."
                    )
                elif profile is not None and profile.is_removed_chef:
                    form_error = (
                        "This chef profile was removed. Register again to request "
                        "a new chef account."
                    )
                    show_chef_reregistration = True
                elif (
                    profile is not None
                    and profile.is_chef
                    and not profile.is_approved_chef
                ):
                    form_error = "Your chef application has not been approved yet."
                elif (
                    selected_role
                    and account_role
                    and account_role != selected_role
                ):
                    account_role_label = profile.get_role_display()
                    form_error = (
                        f"That account is registered as {account_role_label}. "
                        f"Choose {account_role_label} to continue."
                    )
                else:
                    login(request, user)
                    role_label = (
                        profile.get_role_display() if profile is not None else "member"
                    )
                    messages.success(
                        request,
                        f"Welcome back, {user.first_name or user.username}! "
                        f"You’re signing in as {role_label}.",
                    )
                    return redirect(_login_destination(user, next_url))

    selected_role_details = ROLE_DETAILS.get(selected_role, {})
    context = {
        "form_values": form_values,
        "form_error": form_error,
        "show_chef_reregistration": show_chef_reregistration,
        "next_url": next_url,
        "role_options": ROLE_OPTIONS,
        "role": selected_role,
        "role_label": selected_role_details.get("label", ""),
        "role_description": selected_role_details.get("description", ""),
        "selected_role": selected_role,
        "selected_role_label": selected_role_details.get("label", ""),
    }
    return render(
        request,
        "login.html",
        context,
        status=400 if form_error else 200,
    )


def _safe_next_url(request):
    candidate = request.POST.get("next") or request.GET.get("next") or ""
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return reverse("home")


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")
