from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    REQUIRED_FIELDS = ["email", "email_verified"]

    email = models.EmailField(_("Email Address"), unique=True)
    email_verified = models.BooleanField(default=False)
    last_verification_email_sent = models.DateTimeField(null=True, blank=True)
