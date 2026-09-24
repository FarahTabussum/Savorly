from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse


def send_chef_approval_email(user):
    if not user.email:
        raise ValueError("An email address is required to approve this chef.")

    login_url = (
        f"{settings.PUBLIC_SITE_URL.rstrip('/')}{reverse('login')}?role=chef"
    )
    return send_mail(
        subject="Your Savorly chef application is approved",
        message=(
            f"Hi {user.first_name or user.username},\n\n"
            "Your chef application for Savorly has been approved. You can now "
            "sign in and share your recipes with the community.\n\n"
            f"Sign in: {login_url}\n"
            f"Username: {user.username}\n\n"
            "We’re glad to have you at the table.\n"
            "— The Savorly team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
