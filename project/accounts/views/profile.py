from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.conf import settings
from accounts.forms import EmailChangeForm, PasswordChangeForm
# from accounts.tasks import send_email_export_data

from django.contrib.auth.views import PasswordChangeView as BasePasswordChangeView
from django.urls import reverse_lazy


class PasswordChangeView(BasePasswordChangeView):
    form_class = PasswordChangeForm
    template_name = "account/password_change.html"
    success_url = reverse_lazy("accounts:me")

    def form_valid(self, form):
        messages.success(
            self.request, _("Your password has been changed successfully!")
        )
        return super().form_valid(form)


@login_required
def user_profile(request):
    if request.method == "POST":
        # Update notification preferences
        preferences = request.user.notification_preferences
        preferences.unread_messages_notification = (
            request.POST.get("unread_messages_notification") == "on"
        )
        preferences.ride_status_update_notification = (
            request.POST.get("ride_status_update_notification") == "on"
        )
        preferences.ride_sharing_suggestion_notification = (
            request.POST.get("ride_sharing_suggestion_notification") == "on"
        )

        preferences.save()
        messages.success(request, _("Your preferences have been updated."))

    context = {}
    return render(request, "account/detail.html", context)


@login_required
def delete_profile(request):
    if request.method == "POST":
        user = request.user
        user.delete()
        return redirect("accounts:login")
    context = {}
    return render(request, "account/close.html", context)


@login_required
def email_change(request):
    form = EmailChangeForm(request.user)
    if request.method == "POST":
        form = EmailChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your email has been updated. Please verify it.")
            return redirect("accounts:me")

    context = {"form": form}
    return render(request, "account/email_change.html", context)


@login_required
def export(request):
    # Get all the rides for which the user is the driver
    # or has subscribed to
    rides_as_driver = request.user.rides_as_driver.all()
    rides_as_rider = request.user.rides_as_rider.all()

    rides = rides_as_driver | rides_as_rider
    rides = rides.order_by("-start_dt")
    rides = [(ride.driver == request.user, ride) for ride in rides]

    if request.method == "POST":
        # Trigger the task to send the email with the data export
        # send_email_export_data.delay(request.user.pk)
        # return redirect("accounts:me")
        pass
    # Get all the rides for which the user is the driver
    context = {
        "rides": rides,
        "dpo_email": settings.DPO_EMAIL,
    }
    return render(request, "account/data_export.html", context)
