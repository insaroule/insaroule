from uuid import uuid4

from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from multiselectfield import MultiSelectField


class RideManager(models.Manager):
    def count_shared_ride(self, user1, user2):
        """Return the number of rides shared between two users.
        A ride is "shared" if:
        - One user is the driver and the other is a rider.
        Or
        - Both users are riders in the same ride.
        And
        - The ride has ended (end_dt < now).
        """
        return (
            self.filter(
                Q(driver=user1, rider=user2)
                | Q(driver=user2, rider=user1)
                | (Q(rider=user1) & Q(rider=user2)),
                end_dt__lt=timezone.now(),
            )
            .distinct()
            .count()
        )

    def safe_delete(self, ride) -> bool:
        """Soft delete rides delete the ride only if has no riders or if the ride has ended."""
        if ride.rider.count() == 0 or (ride.end_dt and ride.end_dt < timezone.now()):
            ride.delete()
            return True
        return False

    def filter_upcoming(self):
        """
        Function to filter upcoming rides.
        An upcoming ride is defined as a ride that starts today or in the future.
        (date part only, time is ignored)
        """
        return self.filter(
            start_dt__date__gte=timezone.now().date(),
        )


class Ride(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "CASH", _("Cash")
        LYF = "LYF", _("Lyf Pay")
        WIRE = "WIRE", _("Wire Transfer")

    uuid = models.UUIDField(
        verbose_name=_("UUID"),
        primary_key=True,
        editable=False,
        default=uuid4,
    )

    driver = models.ForeignKey(
        verbose_name=_("driver"),
        to="accounts.User",
        help_text=_("The driver of the ride"),
        on_delete=models.CASCADE,
        related_name="rides_as_driver",
    )

    rider = models.ManyToManyField(
        verbose_name=_("rider"),
        to="accounts.User",
        help_text=_("The rider of the ride"),
        related_name="rides_as_rider",
        blank=True,
    )

    start_dt = models.DateTimeField(
        verbose_name=_("start date and time"),
        help_text=_("The start date and time of the ride"),
        null=True,
        blank=True,
    )

    end_dt = models.DateTimeField(
        verbose_name=_("end date and time"),
        help_text=_("The end date and time of the ride"),
        null=True,
        blank=True,
    )

    start_loc = models.ForeignKey(
        verbose_name=_("start location"),
        to="carpool.Location",
        help_text=_("The start location of the ride"),
        related_name="rides_start_here",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    end_loc = models.ForeignKey(
        verbose_name=_("end location"),
        to="carpool.Location",
        help_text=_("The end location of the ride"),
        related_name="rides_end_here",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    steps = models.ManyToManyField(
        verbose_name=_("steps"),
        to="carpool.Step",
        help_text=_("The steps of the ride"),
        related_name="rides",
        blank=True,
    )

    payment_method = MultiSelectField(
        verbose_name=_("payment method"),
        choices=PaymentMethod.choices,
        help_text=_("The payment method for the ride"),
        blank=True,
        default=[PaymentMethod.CASH],
    )

    price = models.FloatField(
        verbose_name=_("price"),
        help_text=_("The price of the ride"),
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
    )

    comment = models.TextField(
        verbose_name=_("comment"),
        help_text=_("Comment about the ride"),
        blank=True,
    )

    seats_offered = models.PositiveIntegerField(
        verbose_name=_("seats offered"),
        help_text=_("Number of seats offered for the ride"),
        validators=[MinValueValidator(1)],
        default=1,
    )

    vehicle = models.ForeignKey(
        verbose_name=_("vehicle"),
        to="carpool.Vehicle",
        help_text=_("The vehicle of the ride"),
        on_delete=models.CASCADE,
    )

    geometry = models.LineStringField(
        verbose_name=_("geometry"),
        help_text=_("Geographical representation of the ride"),
        srid=4326,  # WGS84
        null=True,
        blank=True,
        default=None,
    )

    duration = models.DurationField(
        verbose_name=_("duration"),
        help_text=_("Duration of the ride"),
        null=True,
        blank=True,
    )

    objects = RideManager()

    @property
    def remaining_seats(self):
        return self.seats_offered - self.rider.count()

    @property
    def booked_seats(self):
        return self.rider.count()

    def get_absolute_url(self):
        return reverse("carpool:detail", kwargs={"pk": self.pk})

    class Meta:
        permissions = [
            ("view_ride_statistics", "Can view ride statistics"),
        ]

    def clean(self):
        # Check that seats_oferred is lower or equal to vehicle.seats
        if self.vehicle and self.seats_offered > self.vehicle.seats:
            raise ValidationError(
                {
                    "seats_offered": _(
                        "Seats offered cannot be greater than vehicle seats."
                    )
                }
            )
