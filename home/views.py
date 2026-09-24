from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
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
            "Bring your recipes to the table and build a community of home cooks "
            "who are ready to make your dishes."
        ),
    },
    "admin": {
        "label": "Admin",
        "description": (
            "Create a workspace account to help keep Savorly's recipes and "
            "community running smoothly."
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
    if profile is not None and profile.role == Profile.Role.CHEF:
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

    if request.user.is_authenticated:
        return redirect("home")

    form_values = {"username": "", "email": ""}
    errors = {}

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
        elif not all(character.isalnum() or character in "@.+-_" for character in username):
            errors["username"] = (
                "Use only letters, numbers, and the characters @ . + - _."
            )
        elif User.objects.filter(username__iexact=username).exists():
            errors["username"] = "That username is already taken."

        if email:
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
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                    )
                    Profile.objects.create(user=user, role=role)
            except IntegrityError:
                errors["username"] = "That username is already taken."
            else:
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
            form_error = "Choose User, Chef, or Admin as your account type."
        elif not form_values["username"] or not password:
            form_error = "Enter both your username and password."
        else:
            user = authenticate(
                request,
                username=form_values["username"],
                password=password,
            )
            if user is None:
                form_error = "That username or password doesn’t look right."
            else:
                profile = getattr(user, "profile", None)
                account_role = profile.role if profile is not None else None
                if (
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
