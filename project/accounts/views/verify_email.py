from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import render, redirect
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import get_user_model

from accounts.tasks import send_verification_email
from accounts.tokens import email_verify_token
from datetime import timedelta
from django.utils import timezone

# ============================================================= #
#                   Email verification views                    #
# ============================================================= #
# Verify email send token  : send email to user with a link to verify their email
# verify email sent : confirm that the email has been sent
# Verify email confirm: confirm the email verification
# Verify email complete : redirect the user to the home page after email verification


def verify_email_send_token(request):
    if request.method == "POST":
        if not request.user.email_verified:
            user = request.user
            now = timezone.now()
            cooldown = timedelta(minutes=5)

            if (
                user.last_verification_email_sent
                and now - user.last_verification_email_sent < cooldown
            ):
                remaining = cooldown - (now - user.last_verification_email_sent)
                minutes = int(remaining.total_seconds() // 60) + 1
                messages.warning(
                    request,
                    f"Veuillez patienter {minutes} minute(s) avant de renvoyer un e-mail.",
                )
                return redirect("accounts:verify_email_sent")

            site_base_url = request.scheme + "://" + get_current_site(request).domain
            user_token = email_verify_token.make_token(user)

            send_verification_email.delay(
                user.username, user.pk, user.email, user_token, site_base_url
            )

            user.last_verification_email_sent = now
            user.save(update_fields=["last_verification_email_sent"])

            return redirect("accounts:verify_email_sent")
        else:
            return redirect("accounts:register")

    return render(request, "registration/verify_email/send_token.html")


def verify_email_sent(request):
    return render(request, "registration/verify_email/email_sent.html")


def verify_email_confirm(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = get_user_model().objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        user = None

    if user is not None and email_verify_token.check_token(user, token):
        user.email_verified = True
        user.active = True
        user.save()
        return redirect("accounts:verify_email_complete")
    else:
        messages.error(request, "Verification link is invalid")
    return render(request, "registration/verify_email/confirm.html")


def verify_email_complete(request):
    return render(request, "registration/verify_email/complete.html")
