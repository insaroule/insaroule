from django.contrib.auth.forms import UserCreationForm
from django import forms

from accounts.models import User
from django.utils.translation import gettext_lazy as _


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"]
        email_check = User.objects.filter(email=email)
        if email_check.exists():
            raise forms.ValidationError(
                _("This email is already in use. Please use another email.")
            )

        return email
