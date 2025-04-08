from django.shortcuts import render, redirect
from django.conf import settings
from accounts.forms import RegisterForm


def register(request):
    if settings.ALLOW_REGISTRATION:
        form = RegisterForm()
        if request.method == "POST":
            form = RegisterForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect("login")
        context = {"form": form}
    else:
        context = {"not_allowed": True}
    return render(request, "register.html", context)
